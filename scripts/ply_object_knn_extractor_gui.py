from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

import numpy as np
import open3d as o3d


try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False


def clean_drop_path(path: str) -> str:
    return path.strip().strip("{}")


def load_object_as_point_cloud(object_path: Path, num_sample_points: int) -> o3d.geometry.PointCloud:
    object_path = Path(object_path)
    suffix = object_path.suffix.lower()

    if suffix == ".ply":
        pcd = o3d.io.read_point_cloud(str(object_path))

        if len(pcd.points) == 0:
            raise ValueError("Die Objekt-PLY enthält keine Punkte.")

        return pcd

    if suffix == ".obj":
        mesh = o3d.io.read_triangle_mesh(str(object_path))

        if mesh.is_empty():
            raise ValueError("Die OBJ-Datei konnte nicht als Mesh geladen werden.")

        if not mesh.has_triangles():
            raise ValueError("Die OBJ-Datei enthält keine Dreiecke.")

        mesh.compute_vertex_normals()

        pcd = mesh.sample_points_poisson_disk(
            number_of_points=int(num_sample_points),
            init_factor=5
        )

        if len(pcd.points) == 0:
            raise ValueError("Poisson-Disk-Sampling hat keine Punkte erzeugt.")

        return pcd

    raise ValueError("Objekt muss .obj oder .ply sein.")


def extract_nearest_neighbors_from_scan(
    scan_path: Path,
    object_path: Path,
    num_sample_points: int,
    knn_neighbors: int,
    max_distance: float,
) -> Path:
    scan_path = Path(scan_path)
    object_path = Path(object_path)

    scan_pcd = o3d.io.read_point_cloud(str(scan_path))

    if len(scan_pcd.points) == 0:
        raise ValueError("Die Scan-PLY enthält keine Punkte.")

    object_pcd = load_object_as_point_cloud(
        object_path=object_path,
        num_sample_points=int(num_sample_points)
    )

    scan_points = np.asarray(scan_pcd.points)
    object_points = np.asarray(object_pcd.points)

    kdtree = o3d.geometry.KDTreeFlann(scan_pcd)

    extracted_indices = set()

    for point in object_points:
        k, indices, distances_squared = kdtree.search_knn_vector_3d(
            point,
            int(knn_neighbors)
        )

        for idx, dist_sq in zip(indices, distances_squared):
            dist = float(np.sqrt(dist_sq))

            if max_distance <= 0 or dist <= max_distance:
                extracted_indices.add(int(idx))

    if not extracted_indices:
        raise ValueError(
            "Keine Scan-Punkte extrahiert. "
            "Erhöhe max_distance oder prüfe, ob Objekt und Scan im selben Koordinatensystem liegen."
        )

    extracted_indices = sorted(extracted_indices)

    extracted_pcd = scan_pcd.select_by_index(extracted_indices)

    root = Path(__file__).resolve().parent
    scan_name = scan_path.stem
    object_name = object_path.stem

    output_dir = root / "outputs" / scan_name
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"{object_name}_extracted_from_scan.ply"

    success = o3d.io.write_point_cloud(str(output_file), extracted_pcd)

    if not success:
        raise RuntimeError("Output-PLY konnte nicht geschrieben werden.")

    return output_file


class ObjectKnnExtractorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PLY Object KNN Extractor")
        self.root.geometry("700x430")

        self.scan_path = tk.StringVar()
        self.object_path = tk.StringVar()

        self.num_sample_points = tk.IntVar(value=5000)
        self.knn_neighbors = tk.IntVar(value=1)
        self.max_distance = tk.DoubleVar(value=0.01)

        title = tk.Label(
            root,
            text="Objekt aus Scan per KNN extrahieren",
            font=("Arial", 18, "bold")
        )
        title.pack(pady=15)

        self.create_file_row(
            label="Scan PLY:",
            variable=self.scan_path,
            command=self.select_scan
        )

        self.create_file_row(
            label="Objekt OBJ/PLY:",
            variable=self.object_path,
            command=self.select_object
        )

        self.create_number_row(
            label="Sampling Punkte bei OBJ:",
            variable=self.num_sample_points
        )

        self.create_number_row(
            label="KNN Nachbarn:",
            variable=self.knn_neighbors
        )

        self.create_number_row(
            label="Max Distanz:",
            variable=self.max_distance
        )

        hint = tk.Label(
            root,
            text="Max Distanz <= 0 bedeutet: keine Distanzfilterung",
            fg="gray"
        )
        hint.pack(pady=3)

        drop_text = (
            "Drag & Drop unterstützt für .ply und .obj"
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

        extract_button = tk.Button(
            root,
            text="Extrahieren",
            command=self.extract,
            font=("Arial", 14, "bold"),
            height=2
        )
        extract_button.pack(fill="x", padx=20, pady=10)

        self.status = tk.Label(root, text="", fg="green", wraplength=650)
        self.status.pack(pady=5)

    def create_file_row(self, label, variable, command):
        frame = tk.Frame(self.root)
        frame.pack(fill="x", padx=20, pady=5)

        tk.Label(frame, text=label, width=18, anchor="w").pack(side="left")

        entry = tk.Entry(frame, textvariable=variable)
        entry.pack(side="left", fill="x", expand=True, padx=5)

        tk.Button(frame, text="Auswählen", command=command).pack(side="right")

    def create_number_row(self, label, variable):
        frame = tk.Frame(self.root)
        frame.pack(fill="x", padx=20, pady=5)

        tk.Label(frame, text=label, width=22, anchor="w").pack(side="left")

        entry = tk.Entry(frame, textvariable=variable)
        entry.pack(side="left", fill="x", expand=True, padx=5)

    def select_scan(self):
        path = filedialog.askopenfilename(
            filetypes=[("PLY files", "*.ply"), ("All files", "*.*")]
        )
        if path:
            self.scan_path.set(path)

    def select_object(self):
        path = filedialog.askopenfilename(
            filetypes=[
                ("3D object files", "*.obj *.ply"),
                ("OBJ files", "*.obj"),
                ("PLY files", "*.ply"),
                ("All files", "*.*"),
            ]
        )
        if path:
            self.object_path.set(path)

    def on_drop(self, event):
        path = Path(clean_drop_path(event.data))
        suffix = path.suffix.lower()

        if suffix == ".ply":
            if not self.scan_path.get():
                self.scan_path.set(str(path))
            else:
                self.object_path.set(str(path))

        elif suffix == ".obj":
            self.object_path.set(str(path))

        else:
            messagebox.showwarning(
                "Ungültige Datei",
                "Bitte nur .ply oder .obj Dateien droppen."
            )

    def extract(self):
        try:
            if not self.scan_path.get():
                raise ValueError("Bitte eine Scan-PLY auswählen.")

            if not self.object_path.get():
                raise ValueError("Bitte ein Objekt als .obj oder .ply auswählen.")

            output_file = extract_nearest_neighbors_from_scan(
                scan_path=Path(self.scan_path.get()),
                object_path=Path(self.object_path.get()),
                num_sample_points=int(self.num_sample_points.get()),
                knn_neighbors=int(self.knn_neighbors.get()),
                max_distance=float(self.max_distance.get()),
            )

            self.status.config(text=f"Fertig: {output_file}")

            messagebox.showinfo(
                "Erfolg",
                f"Extrahierte Punkte gespeichert in:\n{output_file}"
            )

        except Exception as e:
            self.status.config(text="")
            messagebox.showerror("Fehler", str(e))


def main():
    if DND_AVAILABLE:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()

    ObjectKnnExtractorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()