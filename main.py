import machine, ssd1306, time, math

i2c = machine.I2C(0, scl=machine.Pin(22), sda=machine.Pin(21))
oled = ssd1306.SSD1306_I2C(128, 64, i2c)

def draw_line(x1, y1, x2, y2, col):
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)
    sx = 1 if x1 < x2 else -1
    sy = 1 if y1 < y2 else -1
    err = dx - dy
    while True:
        oled.pixel(x1, y1, col)
        if x1 == x2 and y1 == y2:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x1 += sx
        if e2 < dx:
            err += dx
            y1 += sy

row_pins = [33, 25, 26, 27, 14, 12, 13]
col_pins = [18, 19, 32, 5, 23]

rows = [machine.Pin(p, machine.Pin.OUT, value=1) for p in row_pins]
cols = [machine.Pin(p, machine.Pin.IN, machine.Pin.PULL_UP) for p in col_pins]

keys_normal = [
    ['shift','none','mode','down','up'],
    ['x','[+]','log','left','right'],
    ['^','√','sin','cos','tan'],
    ['1','2','3','←','c'],
    ['4','5','6','*','/'],
    ['7','8','9','+','-'],
    ['.','0','(',')','=']
]

keys_shifted = [
    ['shift','none','mode','down','up'],
    ['y','[-]','ln','left','right'],
    ['10^','||','asin','acos','atan'],
    ['1','2','3','←','ca'],
    ['4','5','6','!','%'],
    ['7','8','9','M+','M-'],
    ['inf','0+','e','pi','ans']
]

keys = keys_normal

expr = ""
cursor_pos = 0
ANS = 0
history = ""
shift = 0
selected = 0
Mode = "calc"
modes_list = ["calc", "base", "integral", "equation", "system", "matrix", "slope", "graph"]

history_list = []
history_index = -1
memory = 0.0
last_res = 0.0
is_result = False
modified_after_result = False
just_calculated = False

angle_mode = 'rad'

TOKEN_LIST = [
    "math.log10(", "math.log(", "math.sin(", "math.cos(", "math.tan(",
    "math.asin(", "math.acos(", "math.atan(", "math.sqrt(",
    "math.ceil(", "math.floor(", "**", "1e308", "1e-308"
]

class ModeSwitch(Exception):
    pass


def format_title(name):
    nice = name
    mode_map = {
        'calc': 'Calculator',
        'base': 'Base Converter',
        'integral': 'Integral',
        'equation': 'Equation Solver',
        'system': 'System Solver',
        'matrix': 'Matrix',
        'slope': 'Slope',
        'graph': 'Graph'
    }
    if name in mode_map:
        nice = mode_map[name]
    else:
        nice = str(name).strip()

    def cap_word(w):
        if not w: return w
        return w[0].upper() + (w[1:].lower() if len(w) > 1 else '')

    nice = ' '.join([cap_word(w) for w in nice.split()])

    if len(nice) > 16:
        nice = nice[:15] + '…'
    return nice


class MathWrapper:
    def __init__(self, base, use_deg):
        self._m = base
        self._deg = use_deg

    def sin(self, x):
        return self._m.sin(self._to_rad(x)) if self._deg else self._m.sin(x)

    def cos(self, x):
        return self._m.cos(self._to_rad(x)) if self._deg else self._m.cos(x)

    def tan(self, x):
        return self._m.tan(self._to_rad(x)) if self._deg else self._m.tan(x)

    def asin(self, x):
        r = self._m.asin(x)
        return self._to_deg(r) if self._deg else r

    def acos(self, x):
        r = self._m.acos(x)
        return self._to_deg(r) if self._deg else r

    def atan(self, x):
        r = self._m.atan(x)
        return self._to_deg(r) if self._deg else r

    def _to_rad(self, x):
        try:
            if isinstance(x, (int, float)) and x != 0:
                ratio = x / math.pi
                if abs(ratio - round(ratio)) < 1e-9:
                    return x
            return math.radians(x)
        except:
            return x

    def _to_deg(self, x):
        try:
            return self._m.degrees(x)
        except:
            return x

    def __getattr__(self, name):
        return getattr(self._m, name)


def eval_expr(expr, local_vars=None):
    if local_vars is None:
        local_vars = {}
    g = {
        'math': MathWrapper(math, angle_mode == 'deg'),
        'e': math.e,
        'pi': math.pi
    }
    g.update(local_vars)
    return eval(expr, g)

def refresh_display(input_str, mode_name, show_cursor=True, prompt_label=None):
    oled.fill(0)
    
    for i in range(10):
        for x in range(0, 128, 8):
            for j in range(8):
                oled.pixel(x + j, i, 1)
    
    oled.text(format_title(mode_name), 1, 1, 0)
    
    if shift: oled.text("SHIFT", 80, 1, 0)
    
    if mode_name == "calc" and history:
        oled.text(clean_text(history)[:16], 0, 14)
        draw_line(0, 24, 127, 24, 1)

    display_text = clean_text(input_str)
    
    lines = wrap_text(display_text, 16)
    
    start_y = 28 if (mode_name == "calc") else 14

    if prompt_label:
        oled.text(clean_text(str(prompt_label))[:16], 0, 14)
        start_y = 24

    if not input_str and show_cursor:
         oled.text("|", 0, start_y)

    for i, l in enumerate(lines[-3:]):
        oled.text(l, 0, start_y + i*10)
        
    if show_cursor and input_str:
        display_prefix = clean_text(input_str[:cursor_pos])
        display_pos = len(display_prefix)
        cx = (display_pos % 16) * 8
        cy = start_y + (display_pos // 16) * 10
        if cy < 64 and int(time.ticks_ms() / 500) % 2 == 0:
            oled.text("_", cx, cy)

    oled.show()

def wrap_text(text, width):
    lines = []
    while text:
        if len(text) <= width:
            lines.append(text)
            break
        idx = text.rfind(' ', 0, width + 1)
        if idx == -1:
            lines.append(text[:width])
            text = text[width:]
        else:
            lines.append(text[:idx])
            text = text[idx + 1:]
    return lines

def clean_text(text):
    t = text.replace("math.", "")
    t = t.replace("**", "^")
    t = t.replace("log10", "log")
    t = t.replace("1e308", "inf")
    return t

def print_(*args):
    oled.fill(0)
    current_y = 0
    
    for arg in args:
        s = str(arg)
        s = clean_text(s)
        
        lines = wrap_text(s, 16)
        for line in lines:
            oled.text(line, 0, current_y)
            current_y += 10
            if current_y > 54:
                oled.text("...", 110, 54)
                oled.show()
                wait_key()
                oled.fill(0)
                current_y = 0
                
    oled.show()

def wait_key():
    while True:
        k = read_key()
        if k: return k
        time.sleep_ms(10)

def input_(prompt_text):
    inp_str = ""
    global keys, shift
    global cursor_pos

    outer_cursor = cursor_pos
    cursor_pos = 0

    while True:
        keys = keys_shifted if shift else keys_normal

        try:
            refresh_display(inp_str, Mode, show_cursor=True, prompt_label=prompt_text)
        except Exception:
            refresh_display(inp_str, prompt_text, show_cursor=True)

        k = read_key()
        if k == "mode": raise ModeSwitch()

        if k == "=":
            cursor_pos = outer_cursor
            return inp_str
        elif k == "c":
            inp_str = ""
            cursor_pos = 0
        elif k == "←":
            inp_str, cursor_pos = smart_backspace_at(inp_str, cursor_pos)
        elif k == "shift":
            shift = 1 - shift
        elif k:
            if k == 'left':
                if cursor_pos > 0:
                    moved = False
                    for t in sorted(TOKEN_LIST, key=len, reverse=True):
                        l = len(t)
                        if cursor_pos - l >= 0 and inp_str[cursor_pos-l:cursor_pos] == t:
                            cursor_pos -= l
                            moved = True
                            break
                    if not moved:
                        cursor_pos = max(0, cursor_pos - 1)
            elif k == 'right':
                if cursor_pos < len(inp_str):
                    moved = False
                    for t in sorted(TOKEN_LIST, key=len, reverse=True):
                        l = len(t)
                        if cursor_pos + l <= len(inp_str) and inp_str[cursor_pos:cursor_pos+l] == t:
                            cursor_pos += l
                            moved = True
                            break
                    if not moved:
                        cursor_pos = min(len(inp_str), cursor_pos + 1)
            elif k in ["up","down","none"]:
                pass
            else:
                token = get_token(k)
                inp_str = inp_str[:cursor_pos] + token + inp_str[cursor_pos:]
                cursor_pos += len(token)
                if shift and k != 'shift':
                    shift = 0
                    keys = keys_normal

        time.sleep_ms(10)

    cursor_pos = outer_cursor


def select_from_list(options, title):
    sel = 0
    while True:
        oled.fill(0)
        oled.text(format_title(title), 1, 1, 0)
        for i, opt in enumerate(options):
            prefix = '>' if i == sel else ' '
            line = "{} {}".format(prefix, str(opt))
            oled.text(line[:16], 0, 12 + i*10)
        oled.show()

        k = read_key()
        if k == 'up':
            sel = (sel - 1) % len(options)
        elif k == 'down':
            sel = (sel + 1) % len(options)
        elif k == 'right' or k == '=':
            return options[sel]
        elif k == 'mode':
            return None
        time.sleep_ms(100)


def mode_settings():
    global angle_mode
    choice = select_from_list(["Degree", "Radian"], "Settings")
    if not choice:
        return
    if choice == "Degree":
        angle_mode = 'deg'
    else:
        angle_mode = 'rad'
    oled.fill(0)
    oled.text("Settings", 0, 0)
    oled.text("Angle:" + choice[:6], 0, 20)
    oled.show()
    time.sleep_ms(700)
    wait_key()

def smart_backspace(s):
    if not s:
        return ""

    for t in sorted(TOKEN_LIST, key=len, reverse=True):
        if s.endswith(t):
            return s[:-len(t)]

    return s[:-1]


def smart_backspace_at(s, pos):
    if pos <= 0:
        return s, pos

    left = s[:pos]
    right = s[pos:]

    for t in sorted(TOKEN_LIST, key=len, reverse=True):
        if left.endswith(t):
            new_left = left[:-len(t)]
            return new_left + right, len(new_left)

    new_left = left[:-1]
    return new_left + right, len(new_left)

def get_token(k):
    if k == "x": return "x"
    if k == "^": return "**"
    if k == "log": return "math.log10("
    if k == "ln": return "math.log("
    if k == "sin": return "math.sin("
    if k == "cos": return "math.cos("
    if k == "tan": return "math.tan("
    if k == "√": return "math.sqrt("
    if k == "e": return "e"
    if k == "pi": return "pi"
    if k == "[+]": return "math.ceil("
    if k == "[-]": return "math.floor("
    if k == "10^": return "*10**"
    if k == "asin": return "math.asin("
    if k == "acos": return "math.acos("
    if k == "atan": return "math.atan("
    return k

def modes_menu():
    global selected
    while True:
        oled.fill(0)
        for i in range(10):
            for x in range(0, 128, 8):
                for j in range(8):
                    oled.pixel(x + j, i, 1)
        oled.text("MODE SELECT", 20, 1, 0)
        
        start_idx = (selected // 5) * 5
        end_idx = min(start_idx + 5, len(modes_list))
        
        for i in range(start_idx, end_idx):
            y = 12 + (i - start_idx) * 10
            prefix = ">" if i == selected else " "
            name = modes_list[i]
            if name.startswith("mode"): name = name.upper()
            else: name = name[0].upper() + name[1:].lower()
            oled.text("{} {}".format(prefix, name), 0, y)
        
        oled.show()
        
        k = wait_key()
        if k == "up":
            selected = (selected - 1) % len(modes_list)
        elif k == "down":
            selected = (selected + 1) % len(modes_list)
        elif k == "right" or k == "=":
            return modes_list[selected]
        elif k == "mode":
            return "calc"

def mode_integral():
    try:
        f = input_("f(x):")
        a = float(input_("Start:"))
        b = float(input_("End:"))
        n = 500
        dx = (b-a)/n
        total = 0
        x = a
        
        oled.fill(0)
        oled.text("Integrating...", 10, 30)
        oled.show()
        
        for i in range(n):
            if i % 50 == 0:
                if read_key() == "mode": raise ModeSwitch()
                
            try:
                y = eval_expr(f, {"x": x})
                total += y * dx
            except: pass
            x += dx
            
        ANS = total
        print_("Result:", "{:.6f}".format(total))
        wait_key()
    except ModeSwitch: raise

def mode_equation():
    try:
        deg_str = input_("Deg(2/3):")
        try:
            deg = int(float(deg_str))
        except:
            print_("Invalid degree")
            time.sleep(1)
            wait_key()
            return

        if deg == 2:
            try:
                refresh_display("", "equation", show_cursor=False, prompt_label="ax^2+bx+c=0")
            except Exception:
                pass

            def read_float(label):
                while True:
                    s = input_(label)
                    try:
                        return float(s)
                    except:
                        oled.fill(0)
                        oled.text("Invalid number", 0, 20)
                        oled.text("Press any key", 0, 30)
                        oled.show()
                        wait_key()
                        try:
                            refresh_display("", "equation", show_cursor=False, prompt_label="ax^2+bx+c=0")
                        except Exception:
                            pass

            a = read_float("A:")
            b = read_float("B:")
            c = read_float("C:")

            d = b**2 - 4*a*c

            D_txt = "D:{:.6g}".format(d)
            if d >= 0:
                x1 = (-b + math.sqrt(d)) / (2*a)
                x2 = (-b - math.sqrt(d)) / (2*a)
                x1_txt = "x1:{:.6g}".format(x1)
                x2_txt = "x2:{:.6g}".format(x2)
            else:
                real = -b/(2*a)
                imag = math.sqrt(abs(d)) / (2*a)
                x1_txt = "x1:{:.2f}+{:.2f}i".format(real, imag)
                x2_txt = "x2:{:.2f}-{:.2f}i".format(real, imag)

            oled.fill(0)
            oled.text(D_txt[:16], 0, 10)
            oled.text(x1_txt[:16], 0, 24)
            oled.text(x2_txt[:16], 0, 38)
            oled.show()
            wait_key()

        elif deg == 3:
            print_("ax^3+bx^2+cx+d=0")
            a = float(input_("A:"))
            print_(f"{a}x^3+bx^2+cx+d=0")
            b = float(input_("B:"))
            print_(f"{a}x^3+{b}x^2+cx+d=0")
            c = float(input_("C:"))
            print_(f"{a}x^3+{b}x^2+{c}x+d=0")
            d_val = float(input_("D:"))

            x = 0.0
            for i in range(50):
                fx = a*x**3 + b*x**2 + c*x + d_val
                dfx = 3*a*x**2 + 2*b*x + c
                if abs(dfx) < 1e-9: break
                x = x - fx/dfx
            print_("Real Root:", "{:.6g}".format(x))
            time.sleep(2)

        wait_key()
    except ModeSwitch: raise
    except Exception as e: print_("Err:", e); wait_key()

def mode_system():
    try:
        n = int(input_("Num eq (1-6):"))
        if n < 1 or n > 6:
            print_("Invalid n")
            wait_key()
            return

        A = [[0.0 for _ in range(n)] for __ in range(n)]
        b = [0.0 for _ in range(n)]

        for i in range(n):
            for j in range(n):
                A[i][j] = float(input_("a{}{}:".format(i+1, j+1)))
            b[i] = float(input_("b{}:".format(i+1)))

        for k in range(n):
            pivot = k
            maxv = abs(A[k][k])
            for i in range(k+1, n):
                if abs(A[i][k]) > maxv:
                    maxv = abs(A[i][k])
                    pivot = i
            if maxv < 1e-12:
                print_("No unique solution")
                wait_key()
                return
            if pivot != k:
                A[k], A[pivot] = A[pivot], A[k]
                b[k], b[pivot] = b[pivot], b[k]

            for i in range(k+1, n):
                if A[k][k] == 0:
                    continue
                factor = A[i][k] / A[k][k]
                b[i] -= factor * b[k]
                for j in range(k, n):
                    A[i][j] -= factor * A[k][j]

        x = [0.0 for _ in range(n)]
        for i in range(n-1, -1, -1):
            s = b[i]
            for j in range(i+1, n):
                s -= A[i][j] * x[j]
            if abs(A[i][i]) < 1e-12:
                print_("No unique solution")
                wait_key()
                return
            x[i] = s / A[i][i]

        answers = ["x{}: {:.6g}".format(i+1, x[i]) for i in range(n)]
        page = 0
        page_size = 3
        total_pages = (len(answers) + page_size - 1) // page_size

        while True:
            start = page * page_size
            chunk = answers[start:start+page_size]
            oled.fill(0)
            for i, line in enumerate(chunk):
                y = 12 + i*12
                oled.text(line[:16], 0, y)
            footer = "{}/{}".format(page+1, total_pages)
            oled.text(footer, 100, 54)
            oled.show()

            time.sleep_ms(10)

            k = read_key()
            if k == 'mode':
                raise ModeSwitch()
            if k == '=':
                page += 1
                if page >= total_pages:
                    break
                continue
            continue
    except ModeSwitch:
        raise
    except Exception as e:
        print_("Err:", e)
        wait_key()

def mode_matrix():
    try:
        op = float(input_("1:Det 2:Inv"))
        n = int(input_("Size N:"))
        
        mat = []
        for r in range(n):
            oled.fill(0)
            row = []
            for c in range(n):
                oled.text("Mat Row {}".format(r+1), 0, 0)
                if r > 0: oled.text(str(mat[-1]), 0, 10)
                row_str = str(row + ["?"])
                oled.text(row_str, 0, 20)
                oled.show()
                
                val = float(input_("A[{},{}]:".format(r, c)))
                row.append(val)
            mat.append(row)
            
        if op == 1:
            det = get_det(mat, n)
            print_("Det:", det)
        elif op == 2:
            det = get_det(mat, n)
            if abs(det) < 1e-9: print_("Singular!")
            else:
                inv = get_inverse(mat, n)
                for i in range(n):
                    print_("R{}:".format(i+1), inv[i])
                    wait_key()
        wait_key()
    except ModeSwitch: raise
    except Exception as e: print_("Err:", e); wait_key()

def get_det(mat, n):
    temp = [r[:] for r in mat]
    det = 1
    for i in range(n):
        pivot = i
        while pivot < n and temp[pivot][i] == 0: pivot += 1
        if pivot == n: return 0
        if pivot != i:
            temp[i], temp[pivot] = temp[pivot], temp[i]
            det *= -1
        det *= temp[i][i]
        for j in range(i+1, n):
            f = temp[j][i]/temp[i][i]
            for k in range(i+1, n): temp[j][k] -= f*temp[i][k]
    return det

def get_inverse(mat, n):
    aug = [r[:] + [1 if i==j else 0 for j in range(n)] for i,r in enumerate(mat)]
    for i in range(n):
        p = aug[i][i]
        for j in range(i+1, 2*n): aug[i][j] /= p
        for k in range(n):
            if k!=i:
                f = aug[k][i]
                for j in range(i+1, 2*n): aug[k][j] -= f*aug[i][j]
    return [r[n:] for r in aug]

def mode_slope():
    try:
        f = input_("f(x):")
        pt = float(input_("x point:"))
        
        h_values = [1e-5, 1e-6, 1e-7]
        slopes = []
        for h in h_values:
            y2 = eval_expr(f, {"x": pt + h})
            y1 = eval_expr(f, {"x": pt - h})
            m = (y2 - y1) / (2 * h)
            slopes.append(m)
        
        if len(slopes) > 1:
            mean_all = sum(slopes) / len(slopes)
            filtered = [s for s in slopes if abs(s - mean_all) / abs(mean_all) <= 0.5]
            if filtered:
                final_m = sum(filtered) / len(filtered)
            else:
                final_m = mean_all
        else:
            final_m = slopes[0]
        
        print_("Slope m=", "{:.4f}".format(final_m))
        wait_key()
    except ModeSwitch: raise
    except: print_("Math Err"); wait_key()

def mode_graph():
    try:
        f = input_("f(x):")
        g = input_("g(x):")

        have_g = bool(g and g.strip())

        x_center = 0.0
        y_center = 0.0
        scale_x = 20.0
        scale_y = 20.0

        while True:
            oled.fill(0)

            try:
                px0 = 64 + int((0 - x_center) * (128.0 / scale_x))
            except:
                px0 = 64
            try:
                py0 = 32 - int((0 - y_center) * (64.0 / scale_y))
            except:
                py0 = 32

            if 0 <= px0 <= 127:
                draw_line(px0, 0, px0, 63, 1)
            if 0 <= py0 <= 63:
                draw_line(0, py0, 127, py0, 1)

            prev_y_f = None
            prev_y_g = None
            for px in range(128):
                gx = x_center + (px - 64) * (scale_x / 128)
                try:
                    gy_f = eval_expr(f, {"x": gx})
                except:
                    gy_f = None
                gy_g = None
                if have_g:
                    try:
                        gy_g = eval_expr(g, {"x": gx})
                    except:
                        gy_g = None

                if gy_f is not None:
                    py_f = 32 - int((gy_f - y_center) * (64.0 / scale_y))
                    if 0 <= py_f <= 63:
                        oled.pixel(px, py_f, 1)
                        if prev_y_f is not None and abs(prev_y_f - py_f) < 20:
                            draw_line(px-1, prev_y_f, px, py_f, 1)
                        prev_y_f = py_f
                    else:
                        prev_y_f = None

                if have_g and gy_g is not None:
                    py_g = 32 - int((gy_g - y_center) * (64.0 / scale_y))
                    if 0 <= py_g <= 63:
                        oled.pixel(px, py_g, 1)
                        if prev_y_g is not None and abs(prev_y_g - py_g) < 20:
                            draw_line(px-1, prev_y_g, px, py_g, 1)
                        prev_y_g = py_g
                    else:
                        prev_y_g = None

            try:
                f_val = eval_expr(f, {"x": x_center})
            except:
                f_val = None
            g_val = None
            if have_g:
                try:
                    g_val = eval_expr(g, {"x": x_center})
                except:
                    g_val = None

            top_line = ''
            if f_val is not None:
                top_line += 'f({:.3g})={:.3g}'.format(x_center, f_val)
            if have_g:
                top_line += ' ' + ('g({:.3g})={:.3g}'.format(x_center, g_val) if g_val is not None else 'g(-)=nan')
            oled.text(top_line[:16], 0, 0)

            bottom = 'x={:.3g}'.format(x_center)
            oled.text(bottom[:16], 0, 54)

            oled.show()

            k = read_key()
            if k == 'mode':
                raise ModeSwitch()
            elif k == 'left':
                x_center -= 1
            elif k == 'right':
                x_center += 1
            elif k == 'up':
                y_center += 1
            elif k == 'down':
                y_center -= 1
            elif k == '=':
                try:
                    v = input_('x:')
                    if v:
                        x_center = float(v)
                except ModeSwitch:
                    raise
                except:
                    pass
            elif k == '+':
                scale_x = max(0.1, scale_x * 0.8)
                scale_y = max(0.1, scale_y * 0.8)
            elif k == '-':
                scale_x = min(1e6, scale_x * 1.25)
                scale_y = min(1e6, scale_y * 1.25)
            elif k == 'c':
                x_center = 0.0

            sel_px = 64
            if 0 <= py0 <= 63:
                for ty in range(-2, 3):
                    yy = py0 + ty
                    if 0 <= yy <= 63:
                        oled.pixel(sel_px, yy, 1)

            try:
                val_f = eval_expr(f, {"x": x_center})
                py_f_sel = 32 - int((val_f - y_center) * (64.0 / scale_y))
                if 0 <= py_f_sel <= 63:
                    oled.pixel(sel_px, py_f_sel, 1)
            except:
                pass

            time.sleep_ms(100)

    except ModeSwitch:
        raise

def mode_base():
    try:
        choice = select_from_list(['2', '8', '10', '16'], 'To Base')
        if not choice:
            return
        to_base = int(choice)

        dec_in = input_('Dec:')
        try:
            val = float(dec_in)
            intval = int(val)
        except:
            print_('Invalid')
            wait_key()
            return

        total = intval

        if to_base == 2:
            result = bin(total)[2:]
        elif to_base == 8:
            result = oct(total)[2:]
        elif to_base == 10:
            result = str(total)
        elif to_base == 16:
            result = hex(total)[2:].upper()
        else:
            result = 'Invalid base'

        print_('Result:', result)
        wait_key()
    except ModeSwitch:
        raise
    except:
        print_('Error')
        wait_key()

def read_key():
    for r_i, r in enumerate(rows):
        r.value(0)
        for c_i, c in enumerate(cols):
            if c.value() == 0:
                time.sleep_ms(5)
                if c.value() == 0:
                    k = keys[r_i][c_i]
                    while c.value() == 0:
                        time.sleep_ms(5)
                    r.value(1)
                    return k
        r.value(1)
    return None

def process_calculator_key(k):
    global expr, cursor_pos, shift, keys, history, ANS, Mode, history_list, history_index, memory, last_res, is_result, modified_after_result, just_calculated

    keys = keys_shifted if shift else keys_normal

    if k == "mode":
        Mode = "selecting"
        is_result = False
        modified_after_result = False
        return

    if k == "shift":
        shift = 1 - shift
        refresh_display(expr, Mode)
        return

    if k == "none":
        try:
            mode_settings()
        except ModeSwitch:
            raise
        except:
            pass
        return

    if k == "=":
        try:
            open_p = expr.count('(')
            close_p = expr.count(')')
            expr += ')' * (open_p - close_p)
            
            res = eval_expr(expr, {"ans": ANS, "memory": memory})
            
            history = "{}={}".format(clean_text(expr), str(res))
            ANS = res
            last_res = res
            
            history_list.append((expr, str(res)))
            if len(history_list) > 10:
                history_list.pop(0)
            history_index = -1
            
            if isinstance(res, float):
                if abs(res) < 1e-9: res = 0
                expr = "{:.6g}".format(res)
            else:
                expr = str(res)
                
            cursor_pos = len(expr)
            is_result = True
            modified_after_result = False
            just_calculated = True
        except Exception:
            expr = ""
            cursor_pos = 0
            print_("Syntax Error")
            time.sleep(1)
            is_result = False
            modified_after_result = False
            
    elif k == "c":
        expr = ""
        cursor_pos = 0
        is_result = False
        modified_after_result = False
    elif k == "←":
        if cursor_pos > 0:
            expr, cursor_pos = smart_backspace_at(expr, cursor_pos)
        
    elif k == "left":
        if cursor_pos > 0:
            moved = False
            for t in sorted(TOKEN_LIST, key=len, reverse=True):
                l = len(t)
                if cursor_pos - l >= 0 and expr[cursor_pos-l:cursor_pos] == t:
                    cursor_pos -= l
                    moved = True
                    break
            if not moved:
                cursor_pos = max(0, cursor_pos - 1)
    elif k == "right":
        if cursor_pos < len(expr):
            moved = False
            for t in sorted(TOKEN_LIST, key=len, reverse=True):
                l = len(t)
                if cursor_pos + l <= len(expr) and expr[cursor_pos:cursor_pos+l] == t:
                    cursor_pos += l
                    moved = True
                    break
            if not moved:
                cursor_pos = min(len(expr), cursor_pos + 1)
        
    elif k == "up":
        if history_list:
            history_index = (history_index + 1) % len(history_list)
            expr = history_list[history_index][0]
            cursor_pos = len(expr)
            is_result = False
            modified_after_result = False
    elif k == "down":
        if history_list:
            history_index = (history_index - 1) % len(history_list)
            expr = history_list[history_index][0]
            cursor_pos = len(expr)
            is_result = False
            modified_after_result = False
        
    elif k == "M+":
        try:
            val = ANS if (is_result or ANS != 0) else last_res
        except:
            val = last_res
        memory += val
    elif k == "M-":
        try:
            val = ANS if (is_result or ANS != 0) else last_res
        except:
            val = last_res
        memory -= val
    elif k == "ans":
        try:
            oled.fill(0)
            oled.text("MBR:", 0, 10)
            oled.text(str(memory)[:16], 0, 24)
            oled.show()
            wait_key()
        except:
            pass
    elif k == "ca":
        memory = 0.0
        
    elif k:
        if k in ["settings"]: pass
        else:
            token = get_token(k)
            if is_result and not modified_after_result and token not in ["+", "-", "*", "/", "**"]:
                expr = ""
                cursor_pos = 0
            expr = expr[:cursor_pos] + token + expr[cursor_pos:]
            cursor_pos += len(token)
            modified_after_result = True
            if shift and k != 'shift':
                shift = 0
                keys = keys_normal
    
    if shift and k != "shift":
        shift = 0
        keys = keys_normal

def main():
    global Mode, expr, selected, just_calculated, keys, shift
    
    try:
        print_("RMNO21", "CALCULATOR v2", "Booting...")
    except Exception as e:
        print("OLED Error on boot:", str(e))
    
    time.sleep(1)
    
    while True:
        try:
            if Mode == "selecting":
                new_mode = modes_menu()
                if new_mode: Mode = new_mode

            elif Mode == "calc":
                keys = keys_shifted if shift else keys_normal

                refresh_display(expr, "calc")
                if just_calculated:
                    time.sleep(2)
                    just_calculated = False
                k = read_key()
                if k: process_calculator_key(k)
                time.sleep_ms(10)

            else:
                try:
                    if Mode == "base": mode_base()
                    elif Mode == "integral": mode_integral()
                    elif Mode == "equation": mode_equation()
                    elif Mode == "system": mode_system()
                    elif Mode == "matrix": mode_matrix()
                    elif Mode == "slope": mode_slope()
                    elif Mode == "graph": mode_graph()
                    
                    Mode = "calc"
                
                except ModeSwitch:
                    Mode = "selecting"
                    
        except Exception as e:
            print("System Error:", str(e))
            try:
                print_("System Error", str(e))
            except:
                pass
            time.sleep(2)
            Mode = "calc"
            expr = ""

main()
