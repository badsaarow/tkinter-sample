import json
import tkinter as tk
import customtkinter as ctk
import open3d as o3d
import numpy as np
import json
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from PIL import Image, ImageTk
from tkinter import *

def draw_calculated_volume(master, selected_folder):
    # load datasets/volume_data.json
    with open('datasets/' + selected_folder + '/volume_result.json') as json_file:
        data = json.load(json_file)
        print(data)
        # Create a 3D plot
        fig = Figure() # facecolor='#DBDBDB', edgecolor='#DBDBDB')
        ax = fig.add_subplot(111, projection='3d')
        # create text area for displaying the calculated volume
        text_area = tk.Text(master=master, height=14, width=10, bg='#DBDBDB', font=("Century Gothic", 12))
        # scroll_bar = tk.Scrollbar(master)
        # scroll_bar.pack(side=tk.RIGHT)
        text_area.insert(tk.END, "\n")
        
        for item in data:
            ax.scatter(*item["lb"], c='black', marker='<')
            ax.scatter(*item["lt"], c='red', marker='^')
            ax.scatter(*item["rb"], c='black', marker='>')
            ax.scatter(*item["rt"], c='red', marker='^')

            # round volume to 2 decimal places
            item["volume"] = round(item["volume"], 2)
            text_area.insert(tk.END, f"Slice #{item['idx']:03d}:{item['volume']:5.2f}m³, x1:({item['lt'][0]:5.2f},{item['lt'][1]:5.2f}), x2:({item['rt'][0]:5.2f},{item['rt'][1]:5.2f}), y1:({item['lb'][0]:5.2f},{item['lb'][1]:5.2f}), y2:({item['rb'][0]:5.2f},{item['rb'][1]:5.2f}), \u03B81:{item['lg']:5.2f}\u00B0, \u03B82:{item['rg']:5.2f}\u00B0\n")
            if len(item["lb"]) >= 3 and len(item["lt"]) >= 3:
                ax.plot([item["lb"][0], item["lt"][0]], 
                        [item["lb"][1], item["lt"][1]], 
                        zs=[item["lb"][2], item["lt"][2]], c='green')
            if len(item["lb"]) >= 3 and len(item["rb"]) >= 3:
                ax.plot([item["lb"][0], item["rb"][0]], 
                        [item["lb"][1], item["rb"][1]], 
                        zs=[item["lb"][2], item["rb"][2]], c='blue')
            if len(item["lt"]) >= 3 and len(item["rt"]) >= 3:
                ax.plot([item["lt"][0], item["rt"][0]], 
                        [item["lt"][1], item["rt"][1]], 
                        zs=[item["lt"][2], item["rt"][2]], c='yellow')
            if len(item["rb"]) >= 3 and len(item["rt"]) >= 3:
                ax.plot([item["rb"][0], item["rt"][0]], 
                        [item["rb"][1], item["rt"][1]], 
                        zs=[item["rb"][2], item["rt"][2]], c='purple')

                
        points_guide_image = PhotoImage(file='assets/points_guide.png')
        points_guide_label = ctk.CTkLabel(master=master, text="", image=points_guide_image)
        points_guide_label.grid(row=0, column=0, sticky='we')
   
        text_area.config(state='disabled')
        text_area.grid(row=0, column=1, sticky='we')

        # Create a canvas and add it to the tab_point_count frame
        canvas = FigureCanvasTkAgg(fig, master=master)
        canvas.draw()
        canvas.get_tk_widget().grid(row=1, column=0, padx=5, pady=10, sticky='we')

        text_volume = tk.Text(master=master, height=2, width=40, bg='#DBDBDB', fg='#000', borderwidth=0, font=("Century Gothic", 60))
        # scroll_bar = tk.Scrollbar(master)
        # scroll_bar.pack(side=tk.RIGHT)
        text_volume.insert(tk.END, "총 체적: " + str(round(sum(item["volume"] for item in data), 2)) + "m\u00B3 \n")
        text_volume.config(state='disabled')
        text_volume.grid(row=1, column=1, padx=10, sticky='we')  