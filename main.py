from main_tab import MainTabView
import customtkinter as ctk

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("light")
        self.tab_view = MainTabView(master=self)
        print("App.__init__")

if __name__ == "__main__":
    app = App()

    app.geometry("{0}x{1}+0+0".format(app.winfo_screenwidth(), app.winfo_screenheight()))
    # app._state_before_windows_set_titlebar_color = 'zoomed'
    app.columnconfigure(0, weight=1)
    # app.attributes("-fullscreen", "True")
    app.columnconfigure(0, weight=1)
    # app.rowconfigure(0, weight=1)
    app.title("tkinter app")
    app.mainloop()
    app.state("zoomed")
