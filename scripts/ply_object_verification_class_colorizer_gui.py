import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import tkinter as tk
from tkinter import filedialog, messagebox

import numpy as np
import open3d as o3d
from tkinter import ttk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False


# ============================================================================
# Konfiguration
# ============================================================================

CLASS_COLORS_FLOAT = {
    0: (1.0, 0.0, 0.0),  # Rot = nicht verifiziert
    1: (0.0, 1.0, 0.0),  # Grün = verifiziert
}

CLASS_MATERIALS = {
    0: "class_0_not_verified_red",
    1: "class_1_verified_green",
}


# ============================================================================
# Hilfsfunktionen
# ============================================================================

def clean_drop_path(path: str) -> str:
    return path.strip().strip("{}")


def get_scene_id_from_ply(scene_ply: Path) -> str:
    match = re.search(r"scene_\d{3}", scene_ply.name, re.IGNORECASE)
    if not match:
        raise ValueError(
            "Der Dateiname muss scene_001 bis scene_007 enthalten."
        )
    return match.group(0).lower()


def get_phase_dir_from_scene_ply(scene_ply: Path) -> Path:
    scene_dir = scene_ply.parent

    if scene_dir.parent.name.lower() != "scans":
        raise ValueError(
            "Die PLY-Datei muss in dataset/phases/phase_XX/scans/scene_XXX liegen."
        )

    phase_dir = scene_dir.parent.parent

    if not phase_dir.name.lower().startswith("phase_"):
        raise ValueError("phase_XX konnte nicht aus dem Pfad bestimmt werden.")

    return phase_dir


def load_labels(label_file: Path) -> List[Dict]:
    if not label_file.exists():
        raise FileNotFoundError(
            f"Label-Datei nicht gefunden:\n{label_file}"
        )

    data = json.loads(label_file.read_text(encoding="utf-8"))

    scene_id = label_file.name.replace(
        "_object_verification_labels.json",
        ""
    )

    if isinstance(data, dict) and scene_id in data:
        records = data[scene_id]
    elif isinstance(data, list):
        records = data
    else:
        raise ValueError(
            "Unerwartetes JSON-Format."
        )

    if not isinstance(records, list):
        raise ValueError("JSON-Einträge müssen eine Liste sein.")

    return records


def basename_from_path(path_text: str) -> str:
    return str(path_text).replace("\\", "/").split("/")[-1]


def collect_component_labels(records: List[Dict]) -> Dict[str, int]:
    labels = {}

    for rec in records:
        ref_file = rec.get("reference_file", "")
        basename = basename_from_path(ref_file)

        if not basename:
            continue

        stem = Path(basename).stem

        try:
            cls = int(rec.get(
                "ground_truth_class_object_verification",
                0
            ))
        except Exception:
            cls = 0

        cls = 1 if cls == 1 else 0
        labels[stem] = cls

    return labels


def find_component_file(
    root: Path,
    stem: str,
    suffix: str
) -> Optional[Path]:
    direct = root / f"{stem}{suffix}"
    if direct.exists():
        return direct

    matches = list(root.rglob(f"{stem}{suffix}"))
    if matches:
        return matches[0]

    return None


# ============================================================================
# PLY Erstellung
# ============================================================================


# ============================================================================
# OBJ + MTL Erstellung
# ============================================================================

def write_mtl_file(mtl_path: Path):
    content = """newmtl class_0_not_verified_red
Kd 1.0 0.0 0.0
Ka 1.0 0.0 0.0
Ks 0.0 0.0 0.0

newmtl class_1_verified_green
Kd 0.0 1.0 0.0
Ka 0.0 1.0 0.0
Ks 0.0 0.0 0.0
"""
    mtl_path.write_text(content, encoding="utf-8")


def offset_index(value: str, offset: int) -> str:
    if value == "":
        return ""

    idx = int(value)

    if idx < 0:
        return str(idx)

    return str(idx + offset)


def offset_face_token(
    token: str,
    v_offset: int,
    vt_offset: int,
    vn_offset: int,
) -> str:
    parts = token.split("/")

    if len(parts) == 1:
        return offset_index(parts[0], v_offset)

    if len(parts) == 2:
        return "/".join([
            offset_index(parts[0], v_offset),
            offset_index(parts[1], vt_offset),
        ])

    if len(parts) == 3:
        return "/".join([
            offset_index(parts[0], v_offset),
            offset_index(parts[1], vt_offset),
            offset_index(parts[2], vn_offset),
        ])

    return token


def count_obj_indices(lines: List[str]) -> Tuple[int, int, int]:
    v = sum(1 for line in lines if line.startswith("v "))
    vt = sum(1 for line in lines if line.startswith("vt "))
    vn = sum(1 for line in lines if line.startswith("vn "))
    return v, vt, vn


def append_obj_component(
    output_lines: List[str],
    obj_path: Path,
    material_name: str,
    v_offset: int,
    vt_offset: int,
    vn_offset: int,
) -> Tuple[int, int, int]:
    lines = obj_path.read_text(
        encoding="utf-8",
        errors="ignore"
    ).splitlines()

    output_lines.append("")
    output_lines.append(f"o {obj_path.stem}")
    output_lines.append(f"usemtl {material_name}")

    for line in lines:
        stripped = line.strip()

        if not stripped:
            continue

        if stripped.startswith("#"):
            continue

        if stripped.startswith("mtllib "):
            continue

        if stripped.startswith("usemtl "):
            continue

        if stripped.startswith("o "):
            continue

        if stripped.startswith("g "):
            continue

        if stripped.startswith("f "):
            tokens = stripped.split()
            new_tokens = [
                offset_face_token(
                    tok,
                    v_offset,
                    vt_offset,
                    vn_offset,
                )
                for tok in tokens[1:]
            ]
            output_lines.append(
                "f " + " ".join(new_tokens)
            )
        else:
            output_lines.append(line)

    return count_obj_indices(lines)




# ============================================================================
# Hauptlogik
# ============================================================================


def build_component_index(root: Path, suffix: str) -> Dict[str, Path]:
    if not root.exists():
        raise FileNotFoundError(f"Ordner nicht gefunden:\n{root}")

    index = {}

    for p in root.glob(f"*{suffix}"):
        if p.is_file():
            index[p.stem] = p

    return index

def compute_mesh_area(mesh: o3d.geometry.TriangleMesh) -> float:
    if mesh.is_empty() or not mesh.has_triangles():
        return 0.0

    try:
        return float(mesh.get_surface_area())
    except Exception:
        vertices = np.asarray(mesh.vertices)
        triangles = np.asarray(mesh.triangles)

        if len(vertices) == 0 or len(triangles) == 0:
            return 0.0

        tri_vertices = vertices[triangles]
        a = tri_vertices[:, 1] - tri_vertices[:, 0]
        b = tri_vertices[:, 2] - tri_vertices[:, 0]
        areas = 0.5 * np.linalg.norm(np.cross(a, b), axis=1)
        return float(np.sum(areas))


def allocate_points_by_area(mesh_infos, total_points: int):
    areas = np.array([info["area"] for info in mesh_infos], dtype=np.float64)
    area_sum = float(np.sum(areas))

    if area_sum <= 0:
        base = total_points // len(mesh_infos)
        counts = [base] * len(mesh_infos)

        for i in range(total_points - sum(counts)):
            counts[i % len(counts)] += 1

        return counts

    raw = areas / area_sum * int(total_points)
    counts = np.floor(raw).astype(int)

    counts[counts == 0] = 1

    diff = int(total_points) - int(np.sum(counts))

    if diff > 0:
        order = np.argsort(-(raw - np.floor(raw)))
        for i in range(diff):
            counts[order[i % len(order)]] += 1

    elif diff < 0:
        order = np.argsort(counts)[::-1]
        remaining = -diff

        for idx in order:
            if remaining <= 0:
                break

            removable = max(0, counts[idx] - 1)
            take = min(removable, remaining)

            counts[idx] -= take
            remaining -= take

    return counts.tolist()


def create_sampled_colored_ply_from_obj_components(
    labels_by_stem: Dict[str, int],
    obj_index: Dict[str, Path],
    output_file: Path,
    total_sample_points: int,
    progress_callback=None,
) -> Tuple[int, List[str]]:
    missing = []
    mesh_infos = []

    total = len(labels_by_stem)

    for i, (stem, cls) in enumerate(labels_by_stem.items(), start=1):
        if progress_callback:
            progress_callback("sampling", i, total, f"Lade Mesh: {stem}")

        obj_path = obj_index.get(stem)

        if obj_path is None:
            missing.append(f"{stem}.obj")
            continue

        mesh = o3d.io.read_triangle_mesh(str(obj_path))

        if mesh.is_empty() or not mesh.has_triangles():
            continue

        mesh.compute_vertex_normals()
        area = compute_mesh_area(mesh)

        mesh_infos.append({
            "stem": stem,
            "class": cls,
            "mesh": mesh,
            "area": area,
        })

    if not mesh_infos:
        raise ValueError("Keine OBJ-Komponenten zum Sampeln gefunden.")

    point_counts = allocate_points_by_area(
        mesh_infos,
        int(total_sample_points),
    )

    merged = o3d.geometry.PointCloud()

    total_meshes = len(mesh_infos)

    for i, (info, n_points) in enumerate(zip(mesh_infos, point_counts), start=1):
        if progress_callback:
            progress_callback(
                "sampling",
                i,
                total_meshes,
                f"Sample {info['stem']} mit {n_points} Punkten"
            )

        if n_points <= 0:
            continue

        pcd = info["mesh"].sample_points_poisson_disk(
            number_of_points=int(n_points),
            init_factor=5,
        )

        color = np.array(
            CLASS_COLORS_FLOAT[info["class"]],
            dtype=np.float64,
        )

        colors = np.tile(color, (len(pcd.points), 1))
        pcd.colors = o3d.utility.Vector3dVector(colors)

        merged += pcd

    if len(merged.points) == 0:
        raise ValueError("Sampling hat keine Punkte erzeugt.")

    output_file.parent.mkdir(parents=True, exist_ok=True)

    ok = o3d.io.write_point_cloud(
        str(output_file),
        merged,
        write_ascii=False,
        compressed=False,
    )

    if not ok:
        raise RuntimeError(f"PLY konnte nicht geschrieben werden:\n{output_file}")

    return len(mesh_infos), missing



def create_colored_merged_obj(
    labels_by_stem: Dict[str, int],
    obj_index: Dict[str, Path],
    output_obj: Path,
    progress_callback=None,
) -> Tuple[int, List[str]]:
    output_obj.parent.mkdir(parents=True, exist_ok=True)

    output_mtl = output_obj.with_suffix(".mtl")
    write_mtl_file(output_mtl)

    output_lines = [f"mtllib {output_mtl.name}"]

    v_offset = 0
    vt_offset = 0
    vn_offset = 0

    missing = []
    used = 0

    total = len(labels_by_stem)

    for i, (stem, cls) in enumerate(labels_by_stem.items(), start=1):
        if progress_callback:
            progress_callback("obj", i, total, stem)

        obj_path = obj_index.get(stem)

        if obj_path is None:
            missing.append(f"{stem}.obj")
            continue

        material_name = CLASS_MATERIALS[cls]

        dv, dvt, dvn = append_obj_component(
            output_lines=output_lines,
            obj_path=obj_path,
            material_name=material_name,
            v_offset=v_offset,
            vt_offset=vt_offset,
            vn_offset=vn_offset,
        )

        v_offset += dv
        vt_offset += dvt
        vn_offset += dvn
        used += 1

    if used == 0:
        raise ValueError("Keine OBJ-Komponenten konnten geladen werden.")

    output_obj.write_text("\n".join(output_lines), encoding="utf-8")

    return used, missing



def process_scene_ply(
    scene_ply: Path,
    total_sample_points: int,
    progress_callback=None,
) -> str:
    scene_ply = Path(scene_ply).resolve()

    if not scene_ply.exists():
        raise FileNotFoundError(f"Datei nicht gefunden:\n{scene_ply}")

    scene_id = get_scene_id_from_ply(scene_ply)
    phase_dir = get_phase_dir_from_scene_ply(scene_ply)

    label_file = (
        phase_dir
        / "annotations"
        / "progress_tracking"
        / f"{scene_id}_object_verification_labels.json"
    )

    obj_components_dir = phase_dir / "models" / "components"

    records = load_labels(label_file)
    labels_by_stem = collect_component_labels(records)

    if not labels_by_stem:
        raise ValueError("Keine Komponenten in der Label-Datei gefunden.")

    obj_index = build_component_index(obj_components_dir, ".obj")

    root = Path(__file__).resolve().parent
    output_dir = root / "outputs" / scene_ply.stem
    output_dir.mkdir(parents=True, exist_ok=True)

    out_obj = output_dir / f"{scene_id}_object_verification_model_components_colored.obj"
    out_ply = output_dir / f"{scene_id}_object_verification_model_components_colored.ply"

    used_obj, missing_obj = create_colored_merged_obj(
        labels_by_stem=labels_by_stem,
        obj_index=obj_index,
        output_obj=out_obj,
        progress_callback=progress_callback,
    )

    used_sampled, missing_sampled = create_sampled_colored_ply_from_obj_components(
        labels_by_stem=labels_by_stem,
        obj_index=obj_index,
        output_file=out_ply,
        total_sample_points=int(total_sample_points),
        progress_callback=progress_callback,
    )

    msg = (
        f"Fertig für {scene_id}\n\n"
        f"OBJ Output:\n{out_obj}\n"
        f"MTL Output:\n{out_obj.with_suffix('.mtl')}\n\n"
        f"Gesampelte PLY:\n{out_ply}\n\n"
        f"OBJ Komponenten verwendet: {used_obj}\n"
        f"Gesampelte Komponenten: {used_sampled}\n"
        f"Sampling Punkte Zielwert: {total_sample_points}\n"
        f"Komponenten gesamt im Label: {len(labels_by_stem)}\n"
    )

    if missing_obj:
        msg += f"\nFehlende OBJ-Dateien beim OBJ-Merge: {len(missing_obj)}"

    if missing_sampled:
        msg += f"\nFehlende OBJ-Dateien beim Sampling: {len(missing_sampled)}"

    return msg


# ============================================================================
# GUI
# ============================================================================

class ObjectVerificationColorizerGui:
    def __init__(self, root):
        self.root = root
        self.root.title("PLY Object Verification Class Colorizer")
        self.root.geometry("800x360")

        self.scene_ply_path = tk.StringVar()
        self.sample_points = tk.IntVar(value=200000)
        tk.Label(
            root,
            text="Object Verification Components Colorizer",
            font=("Arial", 18, "bold"),
        ).pack(pady=15)

        self.create_file_row(
            "Scene PLY:",
            self.scene_ply_path,
            self.select_scene_ply,
        )

        tk.Label(
            root,
            text=(
                "Wähle die Scene-PLY aus, z.B. "
                "scene_001_pm1_nerf_luma_scene_ReStage_target-x_phase1.ply"
            ),
            fg="gray",
            wraplength=760,
        ).pack(pady=8)

        drop_text = (
            "Drag & Drop unterstützt für .ply"
            if DND_AVAILABLE
            else "Drag & Drop nicht aktiv. Installiere: pip install tkinterdnd2"
        )

        self.drop_area = tk.Label(
            root,
            text=drop_text,
            relief="groove",
            height=5,
            bg="#f4f4f4",
        )
        self.drop_area.pack(fill="x", padx=20, pady=15)

        self.create_number_row(
            "Sampling Punkte:",
            self.sample_points,
        )


        self.ply_progress_label = tk.Label(root, text="PLY Fortschritt: 0 / 0")
        self.ply_progress_label.pack(pady=2)

        self.ply_progress = ttk.Progressbar(
            root,
            orient="horizontal",
            length=760,
            mode="determinate",
        )
        self.ply_progress.pack(padx=20, pady=2)

        self.obj_progress_label = tk.Label(root, text="OBJ Fortschritt: 0 / 0")
        self.obj_progress_label.pack(pady=2)

        self.obj_progress = ttk.Progressbar(
            root,
            orient="horizontal",
            length=760,
            mode="determinate",
        )
        self.obj_progress.pack(padx=20, pady=2)

        if DND_AVAILABLE:
            self.drop_area.drop_target_register(DND_FILES)
            self.drop_area.dnd_bind("<<Drop>>", self.on_drop)

        tk.Button(
            root,
            text="Einfärben und Mergen",
            command=self.convert,
            font=("Arial", 14, "bold"),
            height=2,
        ).pack(fill="x", padx=20, pady=10)

        self.status = tk.Label(
            root,
            text="",
            fg="green",
            wraplength=760,
        )
        self.status.pack(pady=5)

    def create_file_row(self, label, variable, command):
        frame = tk.Frame(self.root)
        frame.pack(fill="x", padx=20, pady=5)

        tk.Label(
            frame,
            text=label,
            width=18,
            anchor="w",
        ).pack(side="left")

        tk.Entry(
            frame,
            textvariable=variable,
        ).pack(
            side="left",
            fill="x",
            expand=True,
            padx=5,
        )

        tk.Button(
            frame,
            text="Auswählen",
            command=command,
        ).pack(side="right")

    def create_number_row(self, label, variable):
        frame = tk.Frame(self.root)
        frame.pack(fill="x", padx=20, pady=5)

        tk.Label(
            frame,
            text=label,
            width=18,
            anchor="w",
        ).pack(side="left")

        tk.Entry(
            frame,
            textvariable=variable,
        ).pack(
            side="left",
            fill="x",
            expand=True,
            padx=5,
        )

    def select_scene_ply(self):
        path = filedialog.askopenfilename(
            filetypes=[
                ("PLY files", "*.ply"),
                ("All files", "*.*"),
            ]
        )

        if path:
            self.scene_ply_path.set(path)

    def on_drop(self, event):
        path = Path(clean_drop_path(event.data))

        if path.is_file() and path.suffix.lower() == ".ply":
            self.scene_ply_path.set(str(path))
        else:
            messagebox.showwarning(
                "Ungültiger Drop",
                "Bitte eine .ply Datei droppen.",
            )

    def convert(self):
        try:
            if not self.scene_ply_path.get():
                raise ValueError("Bitte eine Scene-PLY auswählen.")

            self.ply_progress["value"] = 0
            self.obj_progress["value"] = 0
            self.ply_progress_label.config(text="PLY Fortschritt: 0 / 0")
            self.obj_progress_label.config(text="OBJ Fortschritt: 0 / 0")
            self.status.config(text="Starte Verarbeitung...")
            self.root.update_idletasks()

            msg = process_scene_ply(
                Path(self.scene_ply_path.get()),
                total_sample_points=int(self.sample_points.get()),
                progress_callback=self.update_progress,
            )

            self.status.config(text="Fertig.")
            messagebox.showinfo("Erfolg", msg)

        except Exception as e:
            self.status.config(text="")
            messagebox.showerror("Fehler", str(e))

    def update_progress(self, kind, current, total, stem):
        percent = int((current / total) * 100) if total else 0

        if kind == "ply":
            self.ply_progress["maximum"] = total
            self.ply_progress["value"] = current
            self.ply_progress_label.config(
                text=f"PLY Fortschritt: {current} / {total} ({percent}%)"
            )

        elif kind == "obj":
            self.obj_progress["maximum"] = total
            self.obj_progress["value"] = current
            self.obj_progress_label.config(
                text=f"OBJ Fortschritt: {current} / {total} ({percent}%)"
            )
        elif kind == "sampling":
            self.ply_progress["maximum"] = total
            self.ply_progress["value"] = current
            self.ply_progress_label.config(
                text=f"Sampling Fortschritt: {current} / {total} ({percent}%)"
            )

        self.status.config(text=f"Verarbeite: {stem}")
        self.root.update_idletasks()


# ============================================================================
# Main
# ============================================================================

def main():
    if DND_AVAILABLE:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()

    ObjectVerificationColorizerGui(root)
    root.mainloop()


if __name__ == "__main__":
    main()