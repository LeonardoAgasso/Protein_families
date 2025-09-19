# parse_similar.awk
BEGIN {
    OFS = "\t"
}

# Lines starting with a single quote = family header
/^\047/ {
    gsub(/^[ \t]+|[ \t]+$/, "")        # trim whitespace
    family_line = $0

    # extract text inside quotes
    if (match(family_line, /^'([^']+)'/, m)) {
        fam_name = m[1]
    } else {
        fam_name = family_line
    }

    # everything after the closing quote = subfamily/description
    rest = family_line
    sub(/^'[^']*'[ \t]*/, "", rest)
    gsub(/[ \t]+/, "_", rest)           # replace spaces/tabs with underscores

    next
}

# Lines with protein entries (must contain parentheses)
fam_name && /\(/ {
    line = $0
    gsub(/^[ \t]+|[ \t]+$/, "", line)
    n = split(line, arr, /,/)
    for (i = 1; i <= n; i++) {
        entry = arr[i]
        gsub(/^[ \t]+|[ \t]+$/, "", entry)
        if (match(entry, /^([A-Za-z0-9_]+)[[:space:]]*\(([A-Za-z0-9_.-]+)\)/, m)) {
            print m[1], m[2], fam_name, rest
        }
    }
}
