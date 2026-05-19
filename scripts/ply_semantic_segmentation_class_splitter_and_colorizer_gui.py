from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
from plyfile import PlyData, PlyElement
import numpy as np

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False


VALID_CLASSES = {"environment", "target", "ground"}

CLASS_COLORS = {
    "target": (0, 0, 255),          # Blau
    "ground": (0, 255, 0),          # Grün
    "environment": (255, 0, 0),     # Rot
}


def clean_drop_path(path: str) -> str:
    return path.strip().strip("{}")


def create_colored_vertices(vertices, labels_np):
    num_vertices = len(vertices)

    old_dtype = vertices.dtype.descr

    color_fields = {
        "red": "u1",
        "green": "u1",
        "blue": "u1",
    }

    new_descr = [
        field for field in old_dtype
        if field[0] not in color_fields
    ]

    new_descr.extend([
        ("red", "u1"),
        ("green", "u1"),
        ("blue", "u1"),
    ])

    colored_vertices = np.empty(num_vertices, dtype=new_descr)

    for name in vertices.dtype.names:
        if name not in color_fields:
            colored_vertices[name] = vertices[name]

    for cls, color in CLASS_COLORS.items():
        mask = labels_np == cls
        colored_vertices["red"][mask] = color[0]
        colored_vertices["green"][mask] = color[1]
        colored_vertices["blue"][mask] = color[2]

    return colored_vertices


def split_ply_by_classes(ply_path: Path, txt_path: Path) -> Path:
    ply_path = Path(ply_path)
    txt_path = Path(txt_path)

    ply = PlyData.read(str(ply_path))

    if "vertex" not in ply:
        raise ValueError("Die PLY-Datei enthält kein 'vertex'-Element.")

    vertices = ply["vertex"].data
    num_vertices = len(vertices)

    with open(txt_path, "r", encoding="utf-8") as f:
        labels = [line.strip().lower() for line in f if line.strip()]

    if len(labels) != num_vertices:
        raise ValueError(
            f"Anzahl Labels passt nicht zur Anzahl Punkte.\n"
            f"PLY vertices: {num_vertices}\n"
            f"TXT labels: {len(labels)}"
        )

    unknown = sorted(set(labels) - VALID_CLASSES)
    if unknown:
        raise ValueError(f"Unbekannte Klassen gefunden: {unknown}")

    root = Path(__file__).resolve().parent
    base_name = ply_path.stem

    output_dir = root / "outputs" / base_name
    output_dir.mkdir(parents=True, exist_ok=True)

    labels_np = np.array(labels)

    for cls in sorted(VALID_CLASSES):
        mask = labels_np == cls
        filtered_vertices = vertices[mask]

        out_file = output_dir / f"{base_name}_{cls}.ply"

        vertex_element = PlyElement.describe(filtered_vertices, "vertex")

        out_ply = PlyData(
            [vertex_element],
            text=ply.text,
            byte_order=ply.byte_order,
            comments=ply.comments,
            obj_info=ply.obj_info,
        )

        out_ply.write(str(out_file))

    colored_vertices = create_colored_vertices(vertices, labels_np)

    colored_vertex_element = PlyElement.describe(
        colored_vertices,
        "vertex"
    )

    other_elements = [
        element for element in ply.elements
        if element.name != "vertex"
    ]

    colored_out_file = output_dir / f"{base_name}_colored_class.ply"

    colored_ply = PlyData(
        [colored_vertex_element] + other_elements,
        text=ply.text,
        byte_order=ply.byte_order,
        comments=ply.comments,
        obj_info=ply.obj_info,
    )

    colored_ply.write(str(colored_out_file))

    return output_dir


class PlySplitterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PLY Class Processor")
        self.root.geometry("620x360")

        self.ply_path = tk.StringVar()
        self.txt_path = tk.StringVar()

        title = tk.Label(
            root,
            text="PLY nach Klassen verarbeiten",
            font=("Arial", 18, "bold")
        )
        title.pack(pady=15)

        self.create_file_row(
            label="PLY Datei:",
            variable=self.ply_path,
            command=self.select_ply
        )

        self.create_file_row(
            label="TXT Label-Datei:",
            variable=self.txt_path,
            command=self.select_txt
        )

        drop_text = (
            "Drag & Drop unterstützt für .ply und .txt"
            if DND_AVAILABLE
            else "Drag & Drop nicht aktiv. Installiere: pip install tkinterdnd2"
        )

        self.drop_area = tk.Label(
            root,
            text=drop_text,
            relief="groove",
            height=5,
            bg="#f4f4f4"
        )
        self.drop_area.pack(fill="x", padx=20, pady=15)

        if DND_AVAILABLE:
            self.drop_area.drop_target_register(DND_FILES)
            self.drop_area.dnd_bind("<<Drop>>", self.on_drop)

        convert_button = tk.Button(
            root,
            text="Konvertieren",
            command=self.convert,
            font=("Arial", 14, "bold"),
            height=2
        )
        convert_button.pack(fill="x", padx=20, pady=10)

        self.status = tk.Label(root, text="", fg="green")
        self.status.pack(pady=5)

    def create_file_row(self, label, variable, command):
        frame = tk.Frame(self.root)
        frame.pack(fill="x", padx=20, pady=5)

        tk.Label(frame, text=label, width=16, anchor="w").pack(side="left")

        entry = tk.Entry(frame, textvariable=variable)
        entry.pack(side="left", fill="x", expand=True, padx=5)

        tk.Button(frame, text="Auswählen", command=command).pack(side="right")

    def select_ply(self):
        path = filedialog.askopenfilename(
            filetypes=[("PLY files", "*.ply"), ("All files", "*.*")]
        )
        if path:
            self.ply_path.set(path)

    def select_txt(self):
        path = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if path:
            self.txt_path.set(path)

    def on_drop(self, event):
        path = Path(clean_drop_path(event.data))

        if path.suffix.lower() == ".ply":
            self.ply_path.set(str(path))
        elif path.suffix.lower() == ".txt":
            self.txt_path.set(str(path))
        else:
            messagebox.showwarning(
                "Ungültige Datei",
                "Bitte nur .ply oder .txt Dateien droppen."
            )

    def convert(self):
        try:
            if not self.ply_path.get():
                raise ValueError("Bitte eine PLY-Datei auswählen.")

            if not self.txt_path.get():
                raise ValueError("Bitte eine TXT-Datei auswählen.")

            output_dir = split_ply_by_classes(
                Path(self.ply_path.get()),
                Path(self.txt_path.get())
            )

            self.status.config(text=f"Fertig. Output: {output_dir}")
            messagebox.showinfo(
                "Erfolg",
                f"Dateien wurden gespeichert in:\n{output_dir}"
            )

        except Exception as e:
            self.status.config(text="")
            messagebox.showerror("Fehler", str(e))


def main():
    if DND_AVAILABLE:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()

    app = PlySplitterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()