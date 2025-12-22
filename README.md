# ESP32 Engineering Calculator v2

A high-performance, feature-rich engineering calculator built using **MicroPython**, an **ESP32**, and an **SSD1306 OLED** display. It supports everything from basic arithmetic to calculus, matrix operations, and function graphing.

<img width="1041" height="815" alt="image" src="https://github.com/user-attachments/assets/23ff08c0-cc20-49cd-b041-009015c6f679" />


## 🚀 Features

The calculator is divided into several specialized modes, accessible via a dedicated menu system:

* **Standard Calculator:** Basic arithmetic with support for trigonometry (`sin`, `cos`, `tan`), logarithms (`log`, `ln`), powers, and roots.
* **Graphing Mode:** Visualizes functions  on a Cartesian plane with auto-scaling.
* **Calculus Suite:** * **Numerical Integration:** Uses Simpson's/Trapezoidal logic to find the area under a curve.
* **Slope (Derivative):** Calculates the instantaneous rate of change at a point .


* **Algebraic Solvers:**
* **Equation Solver:** Solves Quadratic (exact) and Cubic (Newton-Raphson method) equations.
* **System of Equations:** Solves  linear systems.


* **Matrix Operations:** Calculate Determinants and Inverses for  matrices.
* **Base Converter:** Convert between Binary, Octal, Decimal, and Hexadecimal.
* **Scientific Features:** * Shift-key functionality for secondary commands.
* Memory registers (M+, M-, Recall, Clear).
* History scrolling to revisit previous calculations.



---

## 🛠 Hardware Requirements

* **Microcontroller:** ESP32 (NodeMCU or similar).
* **Display:** SSD1306 I2C OLED (128x64).
* **Keypad:** 7x5 Matrix Keypad (Customized layout).
* **Firmware:** MicroPython (v1.19 or newer recommended).

### Pin Mapping (Default)

| Component | ESP32 Pin |
| --- | --- |
| **I2C SCL** | GPIO 22 |
| **I2C SDA** | GPIO 21 |
| **Row Pins** | 33, 25, 26, 27, 14, 12, 13 |
| **Col Pins** | 18, 19, 32, 5, 23 |

---

## 💻 Installation

1. **Prepare the ESP32:**
Ensure your ESP32 is flashed with the latest MicroPython firmware. You can use [Thonny IDE](https://thonny.org/) or `esptool.py`.
2. **Install Libraries:**
You need the `ssd1306.py` driver. You can install it via Thonny (Tools -> Manage Packages) or download it manually and upload it to your ESP32.
3. **Upload the Code:**
* Download the `main.py` from this repository.
* Upload `main.py` to the root directory of your ESP32.


4. **Run:**
Restart your ESP32. The "RAMAN CALCULATOR v2" splash screen should appear.

---

## 📖 How to Use

* **Navigation:** Use the **UP/DOWN** arrows to scroll through the Mode Menu. Press **"="** or **RIGHT** to select a mode.
* **Shift Operations:** Press the **SHIFT** key to toggle secondary functions (e.g., changing `sin` to `asin` or `log` to `ln`).
* **Editing:** Use the **LEFT/RIGHT** arrows to move the cursor within an expression. Use **"←"** for backspace (it is smart enough to delete entire functions like `math.sin(` at once).
* **Exiting Modes:** Press the **MODE** button at any time to escape a sub-mode and return to the selection menu.

---

## 🗃 File Structure

* `main.py`: The core application containing the display engine, keypad driver, and mathematical logic.
* `ssd1306.py`: (External dependency) The I2C OLED driver.

---

## 🤝 Contributing

Feel free to fork this project, report bugs, or submit pull requests. I am particularly interested in:

* Implementing  System of Equation solvers.
* Optimizing the OLED refresh rate for smoother graphing.
* Adding complex number support to the standard calculator mode.

**Project Link:** [https://github.com/RMNO21/ESP32-Calculator](https://github.com/RMNO21/ESP32-Calculator)
**Simulator Link:**https://wokwi.com/projects/451010467250938881


