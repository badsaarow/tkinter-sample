import os
import glob
import tkinter as tk
from PIL import Image, ImageTk
import customtkinter as ctk
from tkinter import Frame, PhotoImage

class ImageViewer(Frame):
    def __init__(self, master=None, selected_folder=None, **kwargs):
        super().__init__(master, **kwargs)

        self.root = master
        if selected_folder is None:
            selected_folder = '231117_145855'
        self.selected_folder = selected_folder
        print("selected_folder", selected_folder)
        self.current_folder_color = 'datasets/' + self.selected_folder + '/color/'
        self.current_folder_depth = 'datasets/' + self.selected_folder + '/depth/'
        self.initial_image = self.current_folder_color + '000021.jpg'
        print("initial_image", self.initial_image)
        self.current_image_list = [self.initial_image]
        self.current = 0
        if not os.path.isfile(self.initial_image):
            print(f"File not found: {self.initial_image}")
            return

        self.pil_image = Image.open(self.initial_image)
        self.ctk_image = ctk.CTkImage(self.pil_image)
        self.image = ImageTk.PhotoImage(self.pil_image)

        self.photo_label = ctk.CTkLabel(self, text=self.initial_image, image=self.image, compound=tk.TOP, width=30, height=10)
        self.fill_image_list(self.current_folder_color)

        self.prev_button = ctk.CTkButton(self, text='Prev', command=lambda: self.move(-1))
        self.file_label = ctk.CTkLabel(self, text=self.current_image_list[self.current], width=10)
        self.next_button = ctk.CTkButton(self, text='Next', command=lambda: self.move(+1))
        self.prev_button.grid(row=0, column=0)
        self.file_label.grid(row=0, column=1)        
        self.next_button.grid(row=0, column=2)
        self.photo_label.grid(row=1, column=0, columnspan=3, sticky='w')

        self.move(0)

    def set_folder(self, folder):
        self.selected_folder = folder
        self.current_folder_color = 'datasets/' + self.selected_folder + '/color/'
        self.current_folder_depth = 'datasets/' + self.selected_folder + '/depth/'
        self.fill_image_list(self.current_folder_color)
        self.move(0)

    # get the image file names in the folder_path ascending order
    # ex) datasets/231221_103018 folder/color/*.jpg
    def fill_image_list(self, folder_path):
        print("fill_image_list", folder_path)
        self.current_image_list = glob.glob(folder_path + '/' + '*.jpg')
        # replace \\ with /
        self.current_image_list = [x.replace('\\', '/') for x in self.current_image_list]
        self.current_image_list.sort()
        # print("fill_image_list", self.current_image_list, len(self.current_image_list))

    def get_current_image(self):
        if len(self.current_image_list) == 0:
            print("No image in the folder")
            self.fill_image_list(self.current_folder_color)
        image_list = self.current_image_list
        return image_list[self.current]

    def move(self, delta):
        print("move %d %d " % (self.current, delta))
        if not (0 <= self.current + delta < len(self.current_image_list)):
            tk.messagebox.showinfo('End', 'No more image.')
            return
        self.current += delta
        self.image.file = self.current_image_list[self.current]

        self.pil_image = Image.open(self.image.file)
        self.ctk_image = ctk.CTkImage(self.pil_image)
        self.image = ImageTk.PhotoImage(self.pil_image)


        self.file_label.configure(text=self.current_image_list[self.current])
        self.photo_label.configure(text=self.current_image_list[self.current], image=self.image)
        self.photo_label.update()
        self.file_label.update()
        print("move", self.current, self.current_image_list[self.current])


