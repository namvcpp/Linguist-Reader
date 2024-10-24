import ebooklib
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox, Text, Menu, BOTH, END, WORD, LEFT, X, Y, RIGHT, Frame, Scrollbar, Toplevel, Label, Button
from ebooklib import epub
from bs4 import BeautifulSoup
from PIL import Image, ImageTk
from io import BytesIO
import zipfile
import os
import requests
import translators as ts

class EbookReader(ttk.Window):
    def __init__(self):
        super().__init__(themename='darkly')
        self.geometry("1200x800")
        self.title("Elegant Ebook Reader")

        # Book and interface variables
        self.book_list = []
        self.current_book = None
        self.current_chapter = 0
        self.total_chapters = 0
        self.progress_percentage = 0
        self.highlighted_texts = []

        # Pastel colors for highlighting
        self.pastel_colors = ['#FA9189', '#FCAE7C', '#FFE699', '#F9FFB5', '#B3F5BC', '#D6F6FF', '#E2CBF7', '#D1BDFF']

        self.create_home_interface()

    def create_home_interface(self):
        self.home_frame = ttk.Frame(self)
        self.home_frame.pack(fill=BOTH, expand=True)

        self.title_label = ttk.Label(self.home_frame, text="My Library", font=("Helvetica", 24))
        self.title_label.pack(pady=20)

        self.book_listbox = ttk.Treeview(self.home_frame, columns=("Book"), show='headings')
        self.book_listbox.heading("Book", text="Book Name")
        self.book_listbox.pack(fill=BOTH, expand=True, padx=20, pady=10)
        self.book_listbox.bind('<Double-1>', self.open_book)

        self.open_button = ttk.Button(self.home_frame, text="Open Folder", command=self.open_book_folder, bootstyle="success-outline")
        self.open_button.pack(pady=10)

    def open_book_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.load_books_from_folder(folder)

    def load_books_from_folder(self, folder):
        self.book_list.clear()
        self.book_listbox.delete(*self.book_listbox.get_children())
        for file in os.listdir(folder):
            if file.endswith('.epub'):
                self.book_listbox.insert('', 'end', values=(file,))
                self.book_list.append(os.path.join(folder, file))

    def open_book(self, event):
        selected_item = self.book_listbox.selection()
        if selected_item:
            file_index = self.book_listbox.index(selected_item[0])
            file_path = self.book_list[file_index]
            self.load_book(file_path)

    def load_book(self, file_path):
        self.current_book_path = file_path
        self.current_book = epub.read_epub(file_path)
        self.current_chapter = 0
        self.total_chapters = len(list(self.current_book.get_items_of_type(ebooklib.ITEM_DOCUMENT)))

        self.home_frame.pack_forget()
        self.create_reading_interface()
        self.load_chapter_content()

    def create_reading_interface(self):
        self.reading_frame = ttk.Frame(self)
        self.reading_frame.pack(fill=BOTH, expand=True)

        # Top navigation bar
        self.top_panel = ttk.Frame(self.reading_frame)
        self.top_panel.pack(fill=X, padx=10, pady=5)

        self.progress_bar = ttk.Progressbar(self.top_panel, mode='determinate', maximum=self.total_chapters)
        self.progress_bar.pack(fill=X, pady=5)

        self.next_chapter_button = ttk.Button(self.top_panel, text="Next Chapter", command=self.next_chapter)
        self.next_chapter_button.pack(side=RIGHT, padx=5)

        self.previous_chapter_button = ttk.Button(self.top_panel, text="Previous Chapter", command=self.previous_chapter)
        self.previous_chapter_button.pack(side=RIGHT, padx=5)

        # Text area
        self.text_area = Text(self.reading_frame, wrap=WORD)
        self.text_area.pack(fill=BOTH, expand=True, padx=10, pady=10)

        self.scrollbar = Scrollbar(self.text_area)
        self.scrollbar.pack(side=RIGHT, fill=Y)
        self.text_area.config(yscrollcommand=self.scrollbar.set)

        # Context menu for additional actions on text
        self.context_menu = Menu(self, tearoff=0)
        self.context_menu.add_command(label="Highlight", command=self.choose_highlight_color)
        self.context_menu.add_command(label="Unhighlight", command=self.unhighlight_text)
        self.context_menu.add_command(label="Translate", command=self.translate_text)
        self.context_menu.add_command(label="Dictionary", command=self.lookup_dictionary)
        self.text_area.bind("<Button-3>", self.show_context_menu)

    def load_chapter_content(self):
        self.text_area.delete(1.0, END)
        chapter_items = list(self.current_book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
        if self.current_chapter < len(chapter_items):
            chapter = chapter_items[self.current_chapter]
            soup = BeautifulSoup(chapter.get_body_content(), 'html.parser')
            self.render_html_content(soup)

        self.progress_bar['value'] = self.current_chapter
        self.progress_percentage = (self.current_chapter + 1) / self.total_chapters * 100

    def render_html_content(self, soup):
        for tag in soup.descendants:
            if tag.name == 'h1':
                self.text_area.insert(END, tag.get_text() + "\n\n", "heading1")
            elif tag.name == 'h2':
                self.text_area.insert(END, tag.get_text() + "\n\n", "heading2")
            elif tag.name == 'p':
                self.text_area.insert(END, tag.get_text() + "\n\n", "paragraph")
            elif tag.name == 'img':
                self.render_image(tag)

        self.apply_text_styles()

    def apply_text_styles(self):
        self.text_area.tag_configure("heading1", font=("Arial", 20, "bold"))
        self.text_area.tag_configure("heading2", font=("Arial", 18, "bold"))
        self.text_area.tag_configure("paragraph", font=("Arial", 12))

    def render_image(self, img_tag):
        image_path = img_tag.get('src')
        if image_path:
            try:
                with zipfile.ZipFile(self.current_book_path) as book_zip:
                    with book_zip.open(image_path) as image_file:
                        image_data = image_file.read()
                        image = Image.open(BytesIO(image_data))
                        image = image.resize((800, 600))
                        photo = ImageTk.PhotoImage(image)
                        label = ttk.Label(self.reading_frame, image=photo)
                        label.image = photo  # Keep reference to avoid garbage collection
                        label.pack(pady=10)
            except Exception as e:
                print(f"Error rendering image: {e}")

    def next_chapter(self):
        if self.current_chapter < self.total_chapters - 1:
            self.current_chapter += 1
            self.load_chapter_content()

    def previous_chapter(self):
        if self.current_chapter > 0:
            self.current_chapter -= 1
            self.load_chapter_content()

    def show_context_menu(self, event):
        self.context_menu.post(event.x_root, event.y_root)

    def choose_highlight_color(self):
        color_window = Toplevel(self)
        color_window.title("Choose Highlight Color")
        color_window.geometry("180x120")
        color_window.resizable(False, False)
        color_window.overrideredirect(True)  # Remove window borders
        x, y = self.winfo_pointerx(), self.winfo_pointery()
        color_window.geometry(f"+{x}+{y}")

        row, col = 0, 0
        for color in self.pastel_colors:
            btn = Button(color_window, bg=color, width=4, height=2, command=lambda c=color: self.apply_highlight(c))
            btn.grid(row=row, column=col, padx=5, pady=5)
            col += 1
            if col == 4:
                col = 0
                row += 1

    def apply_highlight(self, color):
        selected_text = self.text_area.get(SEL_FIRST, SEL_LAST)
        if selected_text:
            self.text_area.tag_add("highlight", SEL_FIRST, SEL_LAST)
            self.text_area.tag_configure("highlight", background=color)

    def unhighlight_text(self):
        self.text_area.tag_remove("highlight", SEL_FIRST, SEL_LAST)

    def lookup_dictionary(self):
        selected_text = self.text_area.get(SEL_FIRST, SEL_LAST)
        if selected_text:
            response = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{selected_text}")
            if response.status_code == 200:
                data = response.json()[0]
                word = data.get("word", "")
                phonetic = data.get("phonetic", "")
                origin = data.get("origin", "")
                meanings = data.get("meanings", [])
                definition = meanings[0]["definitions"][0]["definition"] if meanings else "No definition available."
                messagebox.showinfo("Dictionary", f"Word: {word}\nPhonetic: {phonetic}\nOrigin: {origin}\nDefinition: {definition}")
            else:
                messagebox.showerror("Error", "Word not found.")

    def translate_text(self):
        selected_text = self.text_area.get(SEL_FIRST, SEL_LAST)
        if selected_text:
            if len(selected_text) > 1000:
                words = selected_text.split()
                chunks = [' '.join(words[i:i+200]) for i in range(0, len(words), 200)]
                translation = ""
                for chunk in chunks:
                    translation += ts.translate_text(chunk, translator='bing', to_language='vi') + " "
            else:
                translation = ts.translate_text(selected_text, translator='bing', to_language='vi')
            
            messagebox.showinfo("Translation", translation)

if __name__ == '__main__':
    app = EbookReader()
    app.mainloop()