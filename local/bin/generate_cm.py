#!/usr/bin/env python3
import sys, argparse, csv, gzip, re
from collections import defaultdict, Counter
from typing import Dict, Set, IO, Iterable, Tuple, List

FAM_RX = re.compile(r"^(?P<code>(?:PF\d{5}|CL\d{4}))(?:\.(?P<ver>\d+))?$")

def open_maybe_gzip(path: str, mode: str):
    return gzip.open(path, mode + "t") if path.endswith(".gz") else open(path, mode)

def parse_header(line: str) -> str:
    return line[1:].strip().split(".", 1)[0]  # >SPECIES.something -> SPECIES

def stream_blocks(fh: IO[str]) -> Iterable[Tuple[str, List[str]]]:
    species, buf = None, []
    for raw in fh:
        if not raw.strip(): 
            continue
        if raw.startswith(">"):
            if species is not None:
                yield species, buf
            species, buf = parse_header(raw), []
        else:
            buf.append(raw.rstrip("\n"))
    if species is not None:
        yield species, buf

def extract_families(field: str, keep_version: bool) -> List[str]:
    fams = []
    for tok in re.split(r"[,\;\|]", field.strip()):
        tok = tok.strip()
        if not tok or tok.upper() in {"ERROR", "CLAN_ERROR"}:
            continue
        m = FAM_RX.match(tok)
        if m:
            code, ver = m.group("code"), m.group("ver")
            fams.append(f"{code}.{ver}" if (keep_version and ver) else code)
        else:
            fams.append(f"__UNKNOWN__:{tok}")  # mark for audit
    return fams

def build_matrix(infile: str, keep_version: bool, unique_proteins: bool, species_order: str):
    species_counts: Dict[str, Counter] = {}
    all_fams: Set[str] = set()
    unknown_seen: Counter = Counter()

    with open_maybe_gzip(infile, "r") as fh:
        for species, lines in stream_blocks(fh):
            # count unique proteins per family or raw occurrences
            fam_to_ps = defaultdict(set) if unique_proteins else None
            fam_counts = Counter()

            for line in lines:
                parts = line.split()
                if len(parts) < 3: 
                    continue
                protein, famfield = parts[1], parts[2]
                fams = extract_families(famfield, keep_version)
                for f in fams:
                    if f.startswith("__UNKNOWN__:"):
                        unknown_seen[f[12:]] += 1
                        continue
                    if unique_proteins:
                        fam_to_ps[f].add(protein)
                    else:
                        fam_counts[f] += 1

            if unique_proteins:
                fam_counts = Counter({fam: len(ps) for fam, ps in fam_to_ps.items()})

            species_counts[species] = fam_counts
            all_fams.update(fam_counts.keys())

    if species_order == "alpha":
        species_counts = dict(sorted(species_counts.items(), key=lambda kv: kv[0]))

    return species_counts, all_fams, unknown_seen

def write_matrix(outfile: str, species_counts: Dict[str, Counter], fams: Set[str], delim: str):
    fam_list = sorted(fams)  # alphabetical columns
    with open_maybe_gzip(outfile, "w") as out:
        w = csv.writer(out, delimiter=delim, lineterminator="\n")
        w.writerow(["species"] + fam_list)
        for sp, cnt in species_counts.items():
            w.writerow([sp] + [cnt.get(f, 0) for f in fam_list])

def write_unknowns(audit_path: str, unknowns: Counter):
    if not audit_path or not unknowns:
        return
    with open(audit_path, "w") as out:
        out.write("# token\tcount\n")
        for tok, c in unknowns.most_common():
            out.write(f"{tok}\t{c}\n")

def main():
    ap = argparse.ArgumentParser(description="Build species × Pfam matrix from >species blocks.")
    ap.add_argument("input", help="Input file (.gz ok)")
    ap.add_argument("-o", "--output", default="species_pfam_matrix.csv", help="Output CSV (.gz ok)")
    ap.add_argument("--delimiter", default=",", help="CSV delimiter")
    ap.add_argument("--keep-version", action="store_true", help="Keep Pfam version (PF00069.26). Default collapses to PF00069.")
    ap.add_argument("--count-occurrences", action="store_true", help="Count raw lines per family (default counts unique proteins).")
    ap.add_argument("--species-order", choices=["alpha","input"], default="alpha")
    ap.add_argument("--audit-unknown", default="unknown_family_tokens.tsv", help="Write ignored non-Pfam tokens and counts")
    args = ap.parse_args()

    species_counts, fams, unknowns = build_matrix(
        args.input,
        keep_version=args.keep_version if hasattr(args, "keep-version") else args.keep_version,
        unique_proteins=not args.count_occurrences,
        species_order=args.species_order,
    )
    write_matrix(args.output, species_counts, fams, args.delimiter)
    write_unknowns(args.audit_unknown, unknowns)

if __name__ == "__main__":
    sys.exit(main())