
import argparse
import json
import random
from collections import defaultdict
from pathlib import Path
 
 
 

def load_manifest(manifest_path: Path) -> list[dict]:
    """ Read manifest file and return a list of records """
    records = []
    
    with manifest_path.open("r", encoding="utf-8") as f:
        
        for line_number, line in enumerate(f, start=1):
            
            line = line.strip()
            
            if not line:
                
                continue
            try:
                records.append(json.loads(line))
                
            except json.JSONDecodeError as exc:
                
                raise ValueError(
                    f"Linea {line_number} del manifest no es JSON valido: {exc}"
                ) from exc
                
                
    return records


def verify_no_duplicate_ids(records: list[dict]) -> None:
 
    seen = set()
    duplicates = set()
    
    for record in records:
        
        record_id = record.get("id")
        
        if record_id in seen:
            
            duplicates.add(record_id)
            
        seen.add(record_id)
 
    if duplicates:
        raise ValueError(
            f"El manifest tiene {len(duplicates)} IDs duplicados, por ejemplo: "
            f"{sorted(duplicates)[:5]}. Revisa el ETL antes de continuar."
        )
 
 
 

def compute_split_sizes(
    n: int,
    train_ratio: float,
    val_ratio: float,
    test_ratio: float,
    min_per_split: int = 1,
) -> tuple[int, int, int]:
 
    if train_ratio + val_ratio + test_ratio > 1:
        raise ValueError(
            f"Los ratios de train, val y test deben sumar 1, pero suman {train_ratio + val_ratio + test_ratio}"
        )
    if n == 0:
        return 0, 0, 0
 
    if n < 3:
        # Muy pocas imagenes para repartir en tres splits sin dejar alguno
        # vacio de forma garantizada. Todo a train, sin excepciones ni
        # redondeos raros.
        return n, 0, 0
 
    n_test = round(n * test_ratio)
    n_val = round(n * val_ratio)
 
    n_test = max(n_test, min_per_split)
    n_val = max(n_val, min_per_split)
 
    n_train = n - n_val - n_test
 
    if n_train < min_per_split:
        # Ratios muy desbalanceados para un bucket chico: prioriza que train
        # nunca quede vacio o negativo, recortando val/test proporcionalmente.
        n_train = min_per_split
        remaining = n - n_train
        n_val = remaining // 2
        n_test = remaining - n_val
 
    assert n_train + n_val + n_test == n, (
        f"Error interno de split: {n_train}+{n_val}+{n_test} != {n}"
    )
 
    return n_train, n_val, n_test
 

def stratified_split(
    records: list[dict],
    seed: int,
    train_ratio: float,
    val_ratio: float,
    test_ratio: float,
) -> tuple[dict[str, list[dict]], dict]:
 
    if abs((train_ratio + val_ratio + test_ratio) - 1.0) > 1e-6:
        raise ValueError(
            f"Rations must sum 1.0, sums {train_ratio + val_ratio + test_ratio}"
        )
 
    rng = random.Random(seed)
 
    by_style: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        style = record.get("effective_style", "unknown")
        by_style[style].append(record)
 
    splits: dict[str, list[dict]] = {"train": [], "val": [], "test": []}
    per_style_report: dict[str, dict] = {}
    small_style_warnings: list[str] = []
 
    for style, style_records in sorted(by_style.items()):
        shuffled = style_records[:]
        rng.shuffle(shuffled)
 
        n = len(shuffled)
        n_train, n_val, n_test = compute_split_sizes(
            n, train_ratio, val_ratio, test_ratio
        )
 
        splits["train"].extend(shuffled[:n_train])
        splits["val"].extend(shuffled[n_train:n_train + n_val])
        splits["test"].extend(shuffled[n_train + n_val:])
 
        per_style_report[style] = {
            "total": n,
            "train": n_train,
            "val": n_val,
            "test": n_test,
        }
 
        if n_val == 0 or n_test == 0:
            small_style_warnings.append(
                f"{style}: {n} imagenes totales, val={n_val}, test={n_test}"
            )
 
    # Mezcla el orden final entre estilos, para que no queden agrupados
    # dentro de cada archivo de split.
    for split_name in splits:
        rng.shuffle(splits[split_name])
 
    report = {
        "per_style": per_style_report,
        "small_style_warnings": small_style_warnings,
    }
 
    return splits, report




def write_split(records: list[dict], output_path: Path) -> None:
    """Escribe un split a un archivo JSONL."""
    with output_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
 
 
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Split estratificado del manifest de Aegis-Art-Atelier-22K"
    )
    parser.add_argument("--manifest", type=Path, required=True,
                         help="Ruta al manifest.jsonl original")
    parser.add_argument("--output-dir", type=Path, default=Path("."),
                         help="Directorio donde se escriben los tres manifests de salida")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train-ratio", type=float, default=0.86)
    parser.add_argument("--val-ratio", type=float, default=0.12)
    parser.add_argument("--test-ratio", type=float, default=0.02)
    args = parser.parse_args()
 
    print(f"Leyendo manifest: {args.manifest}")
    records = load_manifest(args.manifest)
    print(f"Total de filas leidas: {len(records)}")
 
    verify_no_duplicate_ids(records)
    print("Verificacion de IDs duplicados: OK, ninguno encontrado.")
 
    splits, report = stratified_split(
        records=records,
        seed=args.seed,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        test_ratio=args.test_ratio,
    )
 
    total_in = len(records)
    total_out = sum(len(v) for v in splits.values())
    assert total_in == total_out, (
        f"Verificacion final fallo: entrada={total_in}, salida={total_out}. "
        "No se debe continuar con un split inconsistente."
    )
    print(f"Verificacion final: {total_out} filas repartidas, coincide con la entrada.")
 
    args.output_dir.mkdir(parents=True, exist_ok=True)
 
    for split_name, split_records in splits.items():
        output_path = args.output_dir / f"{split_name}_manifest.jsonl"
        write_split(split_records, output_path)
        print(f"  {split_name}: {len(split_records)} filas -> {output_path}")
 
    summary_path = args.output_dir / "split_summary.json"
    summary = {
        "seed": args.seed,
        "ratios": {
            "train": args.train_ratio,
            "val": args.val_ratio,
            "test": args.test_ratio,
        },
        "totals": {
            "train": len(splits["train"]),
            "val": len(splits["val"]),
            "test": len(splits["test"]),
            "total": total_out,
        },
        "per_style": report["per_style"],
        "small_style_warnings": report["small_style_warnings"],
    }
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\nResumen escrito en: {summary_path}")
 
    if report["small_style_warnings"]:
        print(f"\nAdvertencia: {len(report['small_style_warnings'])} estilos con "
              f"val o test en 0 (dataset demasiado chico para ese estilo):")
        for warning in report["small_style_warnings"]:
            print(f"  - {warning}")
 
 
 
if __name__ == "__main__":
    
    
    main()
 