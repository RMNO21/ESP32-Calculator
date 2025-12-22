import machine, ssd1306, time, math

# ---------- OLED ----------
i2c = machine.I2C(0, scl=machine.Pin(22), sda=machine.Pin(21))
oled = ssd1306.SSD1306_I2C(128, 64, i2c)

def draw_line(x1, y1, x2, y2, col):
    # Bresenham's line algorithm using pixel
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

# ---------- KEYPAD ----------
row_pins = [33, 25, 26, 27, 14, 12, 13]
col_pins = [18, 19, 32, 5, 23]

rows = [machine.Pin(p, machine.Pin.OUT, value=1) for p in row_pins]
cols = [machine.Pin(p, machine.Pin.IN, machine.Pin.PULL_UP) for p in col_pins]

# Key definitions
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
    ['shift','none','mode','down','up'],  # Changed 'settings' to 'mode' for consistency
    ['y','[-]','ln','left','right'],
    ['10^','||','asin','acos','atan'],
    ['1','2','3','←','ca'],
    ['4','5','6','!','%'],
    ['7','8','9','M+','M-'],
    ['inf','0+','e','pi','ans']
]

keys = keys_normal  # Initialize global keys

# ---------- GLOBAL STATE ----------
expr = ""          # Current equation string
cursor_pos = 0     # Cursor position index
ANS = 0            # Last answer
history = ""       # Previous calculation string
shift = 0
selected = 0       # Mode menu selection (starts at 0 for 'calc')
Mode = "calc"
modes_list = ["calc", "base", "integral", "equation", "system", "matrix", "slope", "graph"]  # Added 'system' mode

# New: History and Memory
history_list = []  # List of (expr, result) tuples, max 10
history_index = -1  # For scrolling history
memory = 0.0       # Memory register
last_res = 0.0     # Last calculation result
is_result = False  # Flag to indicate if expr is a result (for editing)
modified_after_result = False  # Flag to indicate if expr has been modified after result
just_calculated = False  # Flag to indicate if a calculation was just performed

# Exception to handle "Mode" button press deep inside functions
class ModeSwitch(Exception):
    pass

# ---------- DISPLAY ENGINE ----------

def refresh_display(input_str, mode_name, show_cursor=True):
    oled.fill(0)
    
    # 1. Header Bar (optimized: use a single pass if possible, but pixel is slow)
    # To speed up, consider pre-drawing to buffer if library supports
    for i in range(10):
        for x in range(0, 128, 8):  # Draw in chunks of 8 pixels for slight speedup
            for j in range(8):
                oled.pixel(x + j, i, 1)
    
    oled.text(mode_name.upper(), 1, 1, 0) # Black text
    
    # Indicators
    if shift: oled.text("SHIFT", 80, 1, 0)  # Show "SHIFT" when active
    
    # 2. History (Small text logic simulated by position)
    if mode_name == "calc" and history:
        oled.text(clean_text(history)[:16], 0, 14)
        draw_line(0, 24, 127, 24, 1) # Separator line

    # 3. Input Area
    # Clean the input for display (remove math. prefix)
    display_text = clean_text(input_str)
    
    # Word-wrap the text
    lines = wrap_text(display_text, 16)
    
    start_y = 28 if (mode_name == "calc") else 14
    
    if not input_str and show_cursor:
         oled.text("|", 0, start_y)
    
    for i, l in enumerate(lines[-3:]): # Show last 3 lines
        oled.text(l, 0, start_y + i*10)
        
    # Draw cursor at current position
    if show_cursor and input_str:
        # Map cursor_pos to display position
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
        # Find the last space before width
        idx = text.rfind(' ', 0, width + 1)
        if idx == -1:
            # No space, break at width
            lines.append(text[:width])
            text = text[width:]
        else:
            lines.append(text[:idx])
            text = text[idx + 1:]
    return lines

def clean_text(text):
    # Makes code readable for humans
    t = text.replace("math.", "")
    t = t.replace("**", "^")
    t = t.replace("log10", "log")
    t = t.replace("1e308", "inf")
    return t

def print_(*args):
    # Advanced print that handles scrolling/wrapping
    oled.fill(0)
    current_y = 0
    
    for arg in args:
        s = str(arg)
        s = clean_text(s)
        
        # Wrap text with word wrapping
        lines = wrap_text(s, 16)
        for line in lines:
            oled.text(line, 0, current_y)
            current_y += 10
            if current_y > 54: # Screen full
                oled.text("...", 110, 54)
                oled.show()
                wait_key() # Wait for user to read
                oled.fill(0)
                current_y = 0
                
    oled.show()

# ---------- INPUT HANDLING ----------

def wait_key():
    while True:
        k = read_key()
        if k: return k
        time.sleep_ms(10)

def input_(prompt_text):
    # Specialized input function that checks for Mode button
    inp_str = ""
    print_(prompt_text)
    
    while True:
        refresh_display(inp_str, prompt_text, show_cursor=True)
        
        k = read_key()
        if k == "mode": raise ModeSwitch()
        
        if k == "=":
            return inp_str
        elif k == "c":
            inp_str = ""
        elif k == "←":
            inp_str = smart_backspace(inp_str)
        elif k:
            if k in ["shift","up","down","left","right","none"]: pass
            else:
                token = get_token(k)
                inp_str += token
        
        time.sleep_ms(10)

def smart_backspace(s):
    # Deletes whole tokens like "math.sin(" instead of just "("
    if not s: return ""
    
    tokens = ["math.sin(", "math.cos(", "math.tan(", "math.log10(", "math.log(", 
              "math.sqrt(", "math.asin(", "math.acos(", "math.atan(", 
              "math.ceil(", "math.floor(", "**", "1e308", "1e-308"]
              
    for t in tokens:
        if s.endswith(t):
            return s[:-len(t)]
            
    return s[:-1] # Default delete 1 char

def get_token(k):
    # Maps key label to Python code
    if k == "x": return "x"
    if k == "^": return "**"
    if k == "log": return "math.log10("
    if k == "ln": return "math.log("
    if k == "sin": return "math.sin("
    if k == "cos": return "math.cos("
    if k == "tan": return "math.tan("
    if k == "√": return "math.sqrt("
    if k == "e": return "math.e"
    if k == "pi": return "math.pi"
    if k == "[+]": return "math.ceil("
    if k == "[-]": return "math.floor("
    if k == "10^": return "*10**"
    if k == "asin": return "math.asin("
    if k == "acos": return "math.acos("
    if k == "atan": return "math.atan("
    return k

# ---------- MODES & LOGIC ----------

def modes_menu():
    global selected
    while True:
        oled.fill(0)
        # Fill white bar (optimized slightly)
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
            # Capitalize nicely
            name = modes_list[i]
            if name.startswith("mode"): name = name.upper()
            else: name = name[0].upper() + name[1:].lower()  # Manual capitalize
            oled.text("{} {}".format(prefix, name), 0, y)  # Use .format() for compatibility
        
        oled.show()
        
        k = wait_key()
        if k == "up":
            selected = (selected - 1) % len(modes_list)  # Wrap around
        elif k == "down":
            selected = (selected + 1) % len(modes_list)  # Wrap around
        elif k == "right" or k == "=":
            return modes_list[selected]
        elif k == "mode":
            return "calc" # Exit to calc

# --- 1. Integral ---
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
            # Check for escape
            if i % 50 == 0:
                if read_key() == "mode": raise ModeSwitch()
                
            try:
                y = eval(f, {"x":x, "math":math, "e":math.e, "pi":math.pi})
                total += y * dx
            except: pass
            x += dx
            
        ANS = total
        print_("Result:", "{:.6f}".format(total))
        wait_key()
    except ModeSwitch: raise

# --- 2. Equation Solver ---
def mode_equation():
    try:
        deg = float(input_("Deg(2/3):"))
        
        if deg == 2:
            print_("ax^2+bx+c=0", "A: (x^2)")
            a = float(input_("A: (x^2)"))
            print_(f"{a}x^2+bx+c=0", "B: (x^1)")
            b = float(input_("B: (x^1)"))
            print_(f"{a}x^2+{b}x+c=0", "C: (x^0)")
            c = float(input_("C: (x^0)"))
            
            d = b**2 - 4*a*c
            
            if d >= 0:
                x1 = (-b + math.sqrt(d))/(2*a)
                x2 = (-b - math.sqrt(d))/(2*a)
                print_("Discrim:", d, "x1:", x1, "x2:", x2)
            else:
                # Complex roots formatted
                real = -b/(2*a)
                imag = math.sqrt(abs(d))/(2*a)
                print_("Discrim:", d, "x1:", "{:.2f}+{:.2f}i".format(real, imag), "x2:", "{:.2f}-{:.2f}i".format(real, imag))
            time.sleep(2)
        
        elif deg == 3:
            print_("ax^3+bx^2+cx+d=0", "A: (x^3)")
            a = float(input_("A: (x^3)"))
            print_(f"{a}x^3+bx^2+cx+d=0", "B: (x^2)")
            b = float(input_("B: (x^2)"))
            print_(f"{a}x^3+{b}x^2+cx+d=0", "C: (x^1)")
            c = float(input_("C: (x^1)"))
            print_(f"{a}x^3+{b}x^2+{c}x+d=0", "D: (x^0)")
            d_val = float(input_("D: (x^0)"))
            
            # Newton-Raphson
            x = 0.0
            for i in range(50):
                fx = a*x**3 + b*x**2 + c*x + d_val
                dfx = 3*a*x**2 + 2*b*x + c
                if abs(dfx) < 1e-9: break
                x = x - fx/dfx
            print_("Real Root:", x)
            time.sleep(2)
            
        wait_key()
    except ModeSwitch: raise
    except Exception as e: print_("Err:", e); wait_key()

# --- 2.5. System of Equations ---
def mode_system():
    try:
        n = int(input_("Num eq (2/3):"))
        
        if n == 2:
            a1 = float(input_("a1:"))
            b1 = float(input_("b1:"))
            c1 = float(input_("c1:"))
            a2 = float(input_("a2:"))
            b2 = float(input_("b2:"))
            c2 = float(input_("c2:"))
            
            det = a1 * b2 - a2 * b1
            if abs(det) < 1e-9:
                print_("No unique solution")
            else:
                x = (c1 * b2 - c2 * b1) / det
                y = (a1 * c2 - a2 * c1) / det
                print_("x:", x, "y:", y)
        
        elif n == 3:
            print_("3 eq not implemented")
        
        wait_key()
    except ModeSwitch: raise
    except Exception as e: print_("Err:", e); wait_key()

# --- 3. Matrix ---
def mode_matrix():
    try:
        op = float(input_("1:Det 2:Inv"))
        n = int(input_("Size N:"))
        
        # Visually nice input (optimized: fill only once per row)
        mat = []
        for r in range(n):
            oled.fill(0)  # Fill once per row
            row = []
            for c in range(n):
                oled.text("Mat Row {}".format(r+1), 0, 0)
                if r > 0: oled.text(str(mat[-1]), 0, 10) # Show prev row
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
    # Gaussian elimination with augmented identity
    aug = [r[:] + [1 if i==j else 0 for j in range(n)] for i,r in enumerate(mat)]
    for i in range(n):
        p = aug[i][i]
        for j in range(i+1, 2*n): aug[i][j] /= p
        for k in range(n):
            if k!=i:
                f = aug[k][i]
                for j in range(i+1, 2*n): aug[k][j] -= f*aug[i][j]
    return [r[n:] for r in aug]

# --- 4. Slope ---
def mode_slope():
    try:
        f = input_("f(x):")
        pt = float(input_("x point:"))
        
        # Compute slopes with different h
        h_values = [1e-5, 1e-6, 1e-7]
        slopes = []
        for h in h_values:
            y2 = eval(f, {"x":pt+h, "math":math})
            y1 = eval(f, {"x":pt-h, "math":math})
            m = (y2 - y1) / (2 * h)
            slopes.append(m)
        
        # Filter outliers: remove if differs by >50% from mean of others
        if len(slopes) > 1:
            mean_all = sum(slopes) / len(slopes)
            filtered = [s for s in slopes if abs(s - mean_all) / abs(mean_all) <= 0.5]
            if filtered:
                final_m = sum(filtered) / len(filtered)
            else:
                final_m = mean_all  # Fallback if all filtered out
        else:
            final_m = slopes[0]
        
        print_("Slope m=", "{:.4f}".format(final_m))
        wait_key()
    except ModeSwitch: raise
    except: print_("Math Err"); wait_key()

# --- 5. Graph ---
def mode_graph():
    try:
        f = input_("f(x):")
        oled.fill(0)
        # Axes
        draw_line(64, 0, 64, 63, 1) # Y axis (Vertical)
        draw_line(0, 32, 127, 32, 1) # X axis (Horizontal)
        
        prev_y = None
        for px in range(128):
            # Check exit
            if px % 10 == 0:
                if read_key() == "mode": raise ModeSwitch()

            # Map pixel x (0..127) to graph x (-10..10)
            gx = (px - 64) * (20/128) 
            try:
                gy = eval(f, {"x":gx, "math":math, "e":math.e})
                # Map graph y to pixel y (0..63). Center is 32
                py = 32 - int(gy * (64/20))
                
                if 0 <= py <= 63:
                    oled.pixel(px, py, 1)
                    if prev_y is not None and abs(prev_y - py) < 20:
                        draw_line(px-1, prev_y, px, py, 1)
                    prev_y = py
                else: prev_y = None
            except: prev_y = None
        
        oled.show()
        wait_key()
    except ModeSwitch: raise

# --- 0.5. Base Conversion ---
def mode_base():
    try:
        expr = input_("Expr (A16+101b):")
        to_base = int(input_("To base:"))
        
        # Parse expression with base suffixes
        def parse_number(s):
            s = s.strip()
            if s.endswith('b') or s.endswith('B'):
                return int(s[:-1], 2)
            elif s.endswith('o') or s.endswith('O'):
                return int(s[:-1], 8)
            elif s.endswith('h') or s.endswith('H'):
                return int(s[:-1], 16)
            else:
                return int(s, 10)  # Default decimal
        
        # Simple parser for + and - operations
        parts = expr.replace(' ', '').split('+')
        total = 0
        for part in parts:
            sub_parts = part.split('-')
            for i, sub in enumerate(sub_parts):
                num = parse_number(sub)
                if i == 0:
                    total += num
                else:
                    total -= num
        
        # Convert result to target base
        if to_base == 2:
            result = bin(total)[2:]
        elif to_base == 8:
            result = oct(total)[2:]
        elif to_base == 10:
            result = str(total)
        elif to_base == 16:
            result = hex(total)[2:].upper()
        else:
            result = "Invalid base"
        
        print_("Result:", result)
        wait_key()
    except ModeSwitch: raise
    except: print_("Error"); wait_key()

# ---------- KEYPAD DRIVER ----------

def read_key():
    for r_i, r in enumerate(rows):
        r.value(0)
        for c_i, c in enumerate(cols):
            if c.value() == 0:
                time.sleep_ms(5)  # Short debounce delay
                if c.value() == 0:  # Confirm press
                    k = keys[r_i][c_i]
                    # Debug: uncomment to check key value
                    # print(k)
                    while c.value() == 0:  # Wait for release
                        time.sleep_ms(5)
                    r.value(1)
                    return k
        r.value(1)
    return None

# ---------- CALCULATOR CORE ----------

def process_calculator_key(k):
    global expr, cursor_pos, shift, keys, history, ANS, Mode, history_list, history_index, memory, last_res, is_result, modified_after_result, just_calculated

    keys = keys_shifted if shift else keys_normal

    # 1. Mode Switch
    if k == "mode":
        Mode = "selecting"
        is_result = False
        modified_after_result = False
        return

    # 2. Shift Toggle
    if k == "shift":
        shift = 1 - shift
        refresh_display(expr, Mode)
        return

    # 3. Calculation
    if k == "=":
        try:
            # Auto-close parentheses
            open_p = expr.count('(')
            close_p = expr.count(')')
            expr += ')' * (open_p - close_p)
            
            res = eval(expr, {"math":math, "e":math.e, "pi":math.pi, "ans":ANS, "memory":memory})
            
            history = "{}={}".format(clean_text(expr), str(res))  # Include result in history
            ANS = res
            last_res = res  # Update last result
            
            # Add to history
            history_list.append((expr, str(res)))
            if len(history_list) > 10:
                history_list.pop(0)
            history_index = -1  # Reset history index
            
            # Format Result
            if isinstance(res, float):
                if abs(res) < 1e-9: res = 0
                expr = "{:.6g}".format(res)
            else:
                expr = str(res)
                
            cursor_pos = len(expr)
            is_result = True  # Mark as result
            modified_after_result = False  # Reset modification flag
            just_calculated = True  # Set flag for 2-sec wait
        except Exception:
            expr = ""
            cursor_pos = 0
            print_("Syntax Error")
            time.sleep(1)
            is_result = False
            modified_after_result = False
            
    # 4. Clear / Backspace
    elif k == "c":
        expr = ""
        cursor_pos = 0
        is_result = False
        modified_after_result = False
    elif k == "←":
        if cursor_pos > 0:
            expr = expr[:cursor_pos-1] + expr[cursor_pos:]
            cursor_pos -= 1
        
    # 5. Cursor Movement
    elif k == "left":
        cursor_pos = max(0, cursor_pos - 1)
    elif k == "right":
        cursor_pos = min(len(expr), cursor_pos + 1)
        
    # 6. History Scrolling (in calc mode)
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
        
    # 7. Memory Operations
    elif k == "M+":
        memory += last_res
    elif k == "M-":
        memory -= last_res
    elif k == "ans":  # MR: Recall memory
        if is_result and not modified_after_result:
            expr = ""
            cursor_pos = 0
        expr = expr[:cursor_pos] + str(memory) + expr[cursor_pos:]
        cursor_pos += len(str(memory))
        modified_after_result = True
    elif k == "ca":  # MC: Clear memory
        memory = 0.0
        
    # 8. Typing
    elif k:
        if k in ["none","settings"]: pass  # Ignore unused
        else:
            token = get_token(k)
            if is_result and not modified_after_result and token not in ["+", "-", "*", "/", "**"]:
                expr = ""
                cursor_pos = 0
            expr = expr[:cursor_pos] + token + expr[cursor_pos:]
            cursor_pos += len(token)
            modified_after_result = True
    
    # Reset shift after non-shift key
    if shift and k != "shift":
        shift = 0
        keys = keys_normal

# ---------- MAIN LOOP ----------

def main():
    global Mode, expr, selected, just_calculated
    
    try:
        print_("ENGINEERING", "CALCULATOR v2", "Initializing...")
    except Exception as e:
        print("OLED Error on boot:", str(e))  # Debug print to terminal
        # Continue without OLED if possible, but since it's critical, perhaps halt or simplify
    
    time.sleep(1)
    
    while True:
        try:
            # --- MENU MODE ---
            if Mode == "selecting":
                new_mode = modes_menu()
                if new_mode: Mode = new_mode

            # --- CALCULATOR MODE ---
            elif Mode == "calc":
                refresh_display(expr, "calc")
                if just_calculated:
                    time.sleep(2)
                    just_calculated = False
                k = read_key()
                if k: process_calculator_key(k)
                time.sleep_ms(10)

            # --- FUNCTION MODES ---
            else:
                try:
                    if Mode == "base": mode_base()
                    elif Mode == "integral": mode_integral()
                    elif Mode == "equation": mode_equation()
                    elif Mode == "system": mode_system()
                    elif Mode == "matrix": mode_matrix()
                    elif Mode == "slope": mode_slope()
                    elif Mode == "graph": mode_graph()
                    
                    # If function finishes normally, go back to calc
                    Mode = "calc" 
                
                except ModeSwitch:
                    # User pressed Mode button inside function
                    Mode = "selecting"
                    
        except Exception as e:
            # Global crash handler
            print("System Error:", str(e))  # Debug print to terminal
            try:
                print_("System Error", str(e))
            except:
                pass  # If OLED fails, skip display
            time.sleep(2)
            Mode = "calc"
            expr = ""

# Start
main()