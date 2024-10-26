import tkinter as tk

# Initialize main tkinter window
root = tk.Tk()
root.title("Currently Pressed Keys")
root.geometry("400x200")
accepted_keys = ["w", "a", "s", "d", "space"]

# Label to display pressed keys
pressed_keys_label = tk.Label(root, text="Pressed Keys: ", font=("Helvetica", 14))
pressed_keys_label.pack(pady=20)

# Set to keep track of currently pressed keys
pressed_keys = set()

# Function to update the label with currently pressed keys
def update_label():
    pressed_keys_label.config(text="Pressed Keys: " + ", ".join(pressed_keys))

# Key press event handler
def on_key_press(event):
    # Add the key symbol to the set
    if event.keysym in accepted_keys:
        pressed_keys.add(event.keysym)
        update_label()

# Key release event handler
def on_key_release(event):
    # Remove the key symbol from the set
    if event.keysym in accepted_keys:
        pressed_keys.discard(event.keysym)
        update_label()

# Bind key press and release events to the tkinter window
root.bind("<KeyPress>", on_key_press)
root.bind("<KeyRelease>", on_key_release)

# Run the tkinter main loop
root.mainloop()

# visual controller accepting key input (multiple keys at once wasd and space only) 
# implment a function that sends the current input esp32