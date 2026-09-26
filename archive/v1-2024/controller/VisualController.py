import tkinter as tk

class get_pressed_keys:
    def __init__(self):
        # Define the keys that are accepted
        self.accepted_keys = ["w", "a", "s", "d"]

        # Set up the tkinter window
        self.root = tk.Tk()
        self.root.title("Currently Pressed Keys")
        self.root.geometry("400x200")

        # Label to display pressed keys
        self.pressed_keys_label = tk.Label(self.root, text="Pressed Keys: ", font=("Helvetica", 14))
        self.pressed_keys_label.pack(pady=20)
        self.keybyte = 0b00000000
        # Set to keep track of currently pressed keys
        self.pressed_keys = set()

        # Bind key press and release events to the tkinter window
        self.root.bind("<KeyPress>", self.on_key_press)
        self.root.bind("<KeyRelease>", self.on_key_release)


    # Display Updates
    def update_label(self):
        self.pressed_keys_label.config(text="Pressed Keys: " + ", "+str(self.keybyte))

    # key press events
    def on_key_press(self, event):
        # Add accepted keys to the set
        if event.keysym in self.accepted_keys:
            if event.keysym == 'w': self.keybyte = self.keybyte | 0b00001000
            if event.keysym == 'a': self.keybyte = self.keybyte | 0b00000100
            if event.keysym == 's': self.keybyte = self.keybyte | 0b00000010
            if event.keysym == 'd': self.keybyte = self.keybyte | 0b00000001

            self.pressed_keys.add(event.keysym)
            self.update_label()

    def on_key_release(self, event):
        # Remove accepted keys from the set
        if event.keysym in self.accepted_keys:
            if event.keysym == 'w': self.keybyte = self.keybyte & 0b11110111
            if event.keysym == 'a': self.keybyte = self.keybyte & 0b11111011
            if event.keysym == 's': self.keybyte = self.keybyte & 0b11111101
            if event.keysym == 'd': self.keybyte = self.keybyte & 0b11111110
            
            self.pressed_keys.discard(event.keysym)
            self.update_label()

    # Get pressed keys
    def get_keys(self):
        # permutation table so that it sends less bits
        # 4 keys to be pressed, 24 combinations, 24/8 = 3 bytes
        return self.keybyte

'''
controller = get_pressed_keys()
controller.root.mainloop()x
'''