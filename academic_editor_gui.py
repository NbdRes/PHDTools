import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import urllib.request
import json
import threading
import re
import difflib

class AcademicEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Academic Editor AI")
        self.root.geometry("1000x800")
        
        self.guidelines_text = ""
        self.chat_messages = [] 
        
        self.setup_ui()
        self.load_models()

    def setup_ui(self):
        # 1. Top Frame (Controls)
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(side=tk.TOP, fill=tk.X)
        
        ttk.Label(top_frame, text="Model:").pack(side=tk.LEFT, padx=5)
        self.model_var = tk.StringVar()
        self.model_dropdown = ttk.Combobox(top_frame, textvariable=self.model_var, state="readonly")
        self.model_dropdown.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(top_frame, text="Refresh Models", command=self.load_models).pack(side=tk.LEFT, padx=5)
        
        self.guidelines_label = ttk.Label(top_frame, text="Guidelines: None loaded")
        self.guidelines_label.pack(side=tk.RIGHT, padx=5)
        ttk.Button(top_frame, text="Load Guidelines", command=self.load_file).pack(side=tk.RIGHT, padx=5)

        # 2. Bottom Frame (Action & Status)
        bottom_frame = ttk.Frame(self.root, padding=10)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.edit_btn = ttk.Button(bottom_frame, text="Edit Text", command=self.start_edit)
        self.edit_btn.pack(side=tk.RIGHT, padx=5)
        
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        ttk.Label(bottom_frame, textvariable=self.status_var).pack(side=tk.LEFT, padx=5)

        # 3. Main Vertical Split
        main_paned = ttk.PanedWindow(self.root, orient=tk.VERTICAL)
        main_paned.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # --- TOP SECTION: EDITOR ---
        editor_paned = ttk.PanedWindow(main_paned, orient=tk.HORIZONTAL)
        main_paned.add(editor_paned, weight=2)
        
        # Input Area
        input_frame = ttk.LabelFrame(editor_paned, text="Input (Paste text here)")
        self.input_text = tk.Text(input_frame, wrap=tk.WORD, font=("Times New Roman", 16), bg="white", fg="black", insertbackground="black")
        self.input_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        editor_paned.add(input_frame, weight=1)
        
        # Output Area
        output_frame = ttk.LabelFrame(editor_paned, text="Output (Edited text)")
        self.output_text = tk.Text(output_frame, wrap=tk.WORD, font=("Times New Roman", 16), bg="white", fg="black", insertbackground="black")
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Visual Tags Definition
        self.output_text.tag_config("deleted", overstrike=1)
        self.output_text.tag_config("added", foreground="#1B4F72") 
        self.output_text.tag_config("reasoning", foreground="#1B4F72", font=("Times New Roman", 14, "italic"))
        editor_paned.add(output_frame, weight=1)

        # --- BOTTOM SECTION: CHAT (WHATSAPP STYLE) ---
        chat_frame = ttk.LabelFrame(main_paned, text="Chat with Editor AI")
        main_paned.add(chat_frame, weight=1)
        
        # Chat Input Area
        chat_input_frame = ttk.Frame(chat_frame, padding=5)
        chat_input_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.chat_entry = ttk.Entry(chat_input_frame, font=("Arial", 14))
        self.chat_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.chat_entry.bind("<Return>", lambda e: self.send_chat())
        
        ttk.Button(chat_input_frame, text="Send", command=self.send_chat).pack(side=tk.RIGHT)

        # Scrollable Canvas for Chat Bubbles
        chat_container = tk.Frame(chat_frame, bg="#E5DDD5")
        chat_container.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        self.chat_canvas = tk.Canvas(chat_container, bg="#E5DDD5", highlightthickness=0)
        scrollbar = ttk.Scrollbar(chat_container, orient="vertical", command=self.chat_canvas.yview)
        
        self.scrollable_chat_frame = tk.Frame(self.chat_canvas, bg="#E5DDD5")
        
        self.scrollable_chat_frame.bind(
            "<Configure>",
            lambda e: self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox("all"))
        )
        
        self.canvas_window = self.chat_canvas.create_window((0, 0), window=self.scrollable_chat_frame, anchor="nw")
        self.chat_canvas.bind("<Configure>", self.on_canvas_configure)
        
        self.chat_canvas.configure(yscrollcommand=scrollbar.set)
        self.chat_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def on_canvas_configure(self, event):
        self.chat_canvas.itemconfig(self.canvas_window, width=event.width)

    def load_models(self):
        try:
            req = urllib.request.Request('http://localhost:11434/api/tags')
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                models = [model['name'] for model in data.get('models', [])]
                self.model_dropdown['values'] = models
                if models:
                    self.model_dropdown.current(0)
                self.status_var.set("Models loaded successfully.")
        except Exception:
            self.status_var.set("Error: Is Ollama running?")

    def load_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt"), ("Markdown", "*.md")])
        if filepath:
            try:
                with open(filepath, 'r', encoding='utf-8') as file:
                    self.guidelines_text = file.read()
                filename = filepath.split('/')[-1]
                self.guidelines_label.config(text=f"Guidelines: {filename}")
                self.status_var.set(f"Loaded {filename}")
                self.chat_messages = []
                
                for widget in self.scrollable_chat_frame.winfo_children():
                    widget.destroy()
                    
            except Exception as e:
                messagebox.showerror("Error", f"Failed to read file: {e}")

    # --- TEXT EDITING LOGIC ---
    def start_edit(self):
        text_to_edit = self.input_text.get("1.0", tk.END).strip()
        selected_model = self.model_var.get()
        
        if not text_to_edit or not selected_model:
            messagebox.showinfo("Wait", "Please paste some text and select a model.")
            return
            
        self.edit_btn.config(state=tk.DISABLED)
        self.status_var.set("Thinking (Editing)...")
        self.output_text.delete("1.0", tk.END)
        
        threading.Thread(target=self.call_ollama_edit, args=(text_to_edit, selected_model), daemon=True).start()

    def call_ollama_edit(self, text, model):
        system_prompt = (
            "You are a STRICT, MINIMALIST academic copyeditor specializing in Computational Humanities.\n"
            "Your ONLY job is to fix obvious typos, blatant grammatical errors, and missing punctuation.\n\n"
            "CRITICAL RULES (STRICTLY ENFORCED):\n"
            "1. MINIMAL INTERVENTION: If a sentence is grammatically valid, DO NOT touch it. Do not change the author's wording, flow, or style.\n"
            "2. PRESERVE PUNCTUATION: DO NOT delete valid commas (e.g., after 'However', or in lists). When in doubt, leave the original punctuation exactly as it is.\n"
            "3. DO NOT hallucinate fixes. Only list changes you actually made.\n"
            "4. JOURNAL GUIDELINES PRIORITY: The journal guidelines provided at the bottom override all general rules.\n\n"
            "OUTPUT FORMAT (CRITICAL XML TAGS):\n"
            "You MUST output your response EXACTLY in this format, using these XML tags:\n\n"
            "<edited_text>\n"
            "[Insert the full edited text here. Maintain all original line breaks. Do not use markdown for edits.]\n"
            "</edited_text>\n\n"
            "<reasoning>\n"
            "[Insert a brief bulleted list of ONLY the objective grammatical or typographical fixes you actually made.]\n"
            "</reasoning>\n\n"
            "Do not include any other text outside of these tags.\n\n"
            f"JOURNAL GUIDELINES:\n{self.guidelines_text}"
        )
        
        data = {"model": model, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": text}], "stream": False}
        
        try:
            req = urllib.request.Request('http://localhost:11434/api/chat', data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode())
                reply = result.get('message', {}).get('content', '')
                reply = re.sub(r'<think>.*?</think>', '', reply, flags=re.DOTALL).strip()
                self.root.after(0, self.update_output, text, reply)
        except Exception as e:
            self.root.after(0, self.update_output, text, f"Error: {str(e)}")

    def update_output(self, original_text, response_text):
        self.output_text.delete("1.0", tk.END)
        
        if response_text.startswith("Error:"):
            self.output_text.insert(tk.END, response_text)
            self.edit_btn.config(state=tk.NORMAL)
            self.status_var.set("Ready")
            return

        text_match = re.search(r'<edited_text>(.*?)</edited_text>', response_text, re.DOTALL | re.IGNORECASE)
        reason_match = re.search(r'<reasoning>(.*?)</reasoning>', response_text, re.DOTALL | re.IGNORECASE)

        if text_match:
            edited_text = text_match.group(1).strip()
        else:
            edited_text = response_text.replace("Here is the corrected version of your text:", "").strip()
            if "REASONING:" in edited_text:
                edited_text = edited_text.split("REASONING:")[0].strip()

        reasoning_text = reason_match.group(1).strip() if reason_match else ""

        orig_tokens = [t for t in re.split(r'(\s+)', original_text) if t]
        edit_tokens = [t for t in re.split(r'(\s+)', edited_text) if t]
        
        matcher = difflib.SequenceMatcher(None, orig_tokens, edit_tokens)
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                self.output_text.insert(tk.END, "".join(orig_tokens[i1:i2]))
            elif tag == 'delete':
                self.output_text.insert(tk.END, "".join(orig_tokens[i1:i2]), "deleted")
            elif tag == 'insert':
                self.output_text.insert(tk.END, "".join(edit_tokens[j1:j2]), "added")
            elif tag == 'replace':
                self.output_text.insert(tk.END, "".join(orig_tokens[i1:i2]), "deleted")
                self.output_text.insert(tk.END, "".join(edit_tokens[j1:j2]), "added")
        
        if reasoning_text:
            self.output_text.insert(tk.END, "\n\n--- Editor's Notes ---\n" + reasoning_text, "reasoning")
                
        self.edit_btn.config(state=tk.NORMAL)
        self.status_var.set("Ready")

    # --- ADVANCED WHATSAPP-STYLE CHAT BUBBLES (WITH COPY SUPPORT) ---
    def create_chat_bubble(self, parent, text, is_user):
        frame = tk.Frame(parent, bg="#E5DDD5")
        
        max_text_width = 600
        bg_color = "#DCF8C6" if is_user else "#FFFFFF"
        text_color = "black"
        
        padx, pady = 15, 12
        tail_w = 12
        r = 15 
        
        # Temporary canvas to measure text bounds exactly
        temp_canvas = tk.Canvas(frame)
        text_id = temp_canvas.create_text(0, 0, text=text, font=("Arial", 14), width=max_text_width, anchor="nw")
        bbox = temp_canvas.bbox(text_id)
        temp_canvas.destroy()
        
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        
        bw = tw + padx * 2
        bh = th + pady * 2
        
        cw = bw + tail_w
        ch = bh
        
        canvas = tk.Canvas(frame, width=cw, height=ch, bg="#E5DDD5", highlightthickness=0)
        
        x1 = 0 if is_user else tail_w
        y1 = 0
        x2 = bw if is_user else bw + tail_w
        y2 = bh
        
        # Draw background shapes
        ov1 = canvas.create_oval(x1, y1, x1+2*r, y1+2*r, fill=bg_color, outline="")
        ov2 = canvas.create_oval(x2-2*r, y1, x2, y1+2*r, fill=bg_color, outline="")
        ov3 = canvas.create_oval(x1, y2-2*r, x1+2*r, y2, fill=bg_color, outline="")
        ov4 = canvas.create_oval(x2-2*r, y2-2*r, x2, y2, fill=bg_color, outline="")
        
        rect1 = canvas.create_rectangle(x1+r, y1, x2-r, y2, fill=bg_color, outline="")
        rect2 = canvas.create_rectangle(x1, y1+r, x2, y2-r, fill=bg_color, outline="")
        
        if is_user:
            tail = canvas.create_polygon(x2-r, y1, x2+tail_w, y1, x2-r, y1+15, fill=bg_color, outline="")
        else:
            tail = canvas.create_polygon(x1+r, y1, x1-tail_w, y1, x1+r, y1+15, fill=bg_color, outline="")
            
        # Draw selectable text on top
        text_x = x1 + padx
        text_y = y1 + pady
        
        selectable_text = tk.Text(canvas, font=("Arial", 14), bg=bg_color, fg=text_color, 
                                  wrap=tk.WORD, bd=0, highlightthickness=0, padx=0, pady=0)
        selectable_text.insert("1.0", text)
        selectable_text.configure(insertbackground=bg_color) # Hides the blinking cursor
        
        # Make it read-only but allow copy (Ctrl+C / Cmd+C)
        def block_edit(event):
            if event.state & 4 or event.state & 8: 
                return None
            if event.keysym in ["Up", "Down", "Left", "Right", "Home", "End", "Page_Up", "Page_Down"]:
                return None
            return "break"
            
        selectable_text.bind("<Key>", block_edit)
        selectable_text.bind("<<Paste>>", lambda e: "break")
        selectable_text.bind("<<Cut>>", lambda e: "break")
        
        # Embed the text widget perfectly over the canvas shapes
        canvas.create_window(text_x, text_y, window=selectable_text, anchor="nw", width=tw+2, height=th+2)
        
        canvas.pack()
        return frame

    def append_to_chat(self, text, is_user):
        row_frame = tk.Frame(self.scrollable_chat_frame, bg="#E5DDD5")
        row_frame.pack(fill=tk.X, padx=10, pady=5)
        
        bubble = self.create_chat_bubble(row_frame, text, is_user)
        
        if is_user:
            bubble.pack(side=tk.RIGHT)
        else:
            bubble.pack(side=tk.LEFT)
            
        self.chat_canvas.update_idletasks()
        self.chat_canvas.yview_moveto(1.0)

    def send_chat(self):
        user_msg = self.chat_entry.get().strip()
        selected_model = self.model_var.get()
        
        if not user_msg or not selected_model:
            return
            
        self.chat_entry.delete(0, tk.END)
        self.append_to_chat(user_msg, is_user=True)
        self.status_var.set("Thinking (Chat)...")
        
        if not self.chat_messages:
            sys_prompt = f"You are an expert academic copyeditor specializing in Computational Humanities. Discuss editing choices with the author concisely and helpfully. Adhere strictly to these journal guidelines if applicable:\n{self.guidelines_text}"
            self.chat_messages.append({"role": "system", "content": sys_prompt})
            
        self.chat_messages.append({"role": "user", "content": user_msg})
        
        threading.Thread(target=self.call_ollama_chat, args=(selected_model,), daemon=True).start()

    def call_ollama_chat(self, model):
        data = {"model": model, "messages": self.chat_messages, "stream": False}
        
        try:
            req = urllib.request.Request('http://localhost:11434/api/chat', data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode())
                reply = result.get('message', {}).get('content', '')
                reply = re.sub(r'<think>.*?</think>', '', reply, flags=re.DOTALL).strip()
                
                self.chat_messages.append({"role": "assistant", "content": reply})
                self.root.after(0, lambda: self.append_to_chat(reply, is_user=False))
                self.root.after(0, lambda: self.status_var.set("Ready"))
        except Exception as e:
            self.root.after(0, lambda: self.append_to_chat(f"Error: {str(e)}", is_user=False))
            self.root.after(0, lambda: self.status_var.set("Ready"))

if __name__ == "__main__":
    root = tk.Tk()
    app = AcademicEditorApp(root)
    root.mainloop()
