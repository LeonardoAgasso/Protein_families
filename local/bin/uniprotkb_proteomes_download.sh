#!/usr/bin/env bash

set -Eeuo pipefail

# read the first argument as S
S=${1:-""}
lc_S=$(echo "$S" | tr '[:upper:]' '[:lower:]')

FTP_URL="https://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/reference_proteomes/"$S"/"
OUTPUT_DIR="./"$lc_S"_proteomes/"
DOWNLOAD_DIR="$OUTPUT_DIR/download/"
LIST_FILE=$lc_S"_proteomes.txt"

mkdir -p "$OUTPUT_DIR"	#create output folder
mkdir -p "$DOWNLOAD_DIR"
: > "$LIST_FILE"

echo "Listing subfolders from $FTP_URL ..."

mapfile -t SUBDIRS < <(curl -fsSL "$FTP_URL" | grep -Eo 'href="UP[0-9]{6}[0-9]+/"' | sed -E 's/^href="(.*)\/"$/\1\//' | sort -u)

echo "Found ${#SUBDIRS[@]} proteomes"

for sub in "${SUBDIRS[@]}"; do

	proteome_url="${FTP_URL}${sub}"
	sub_name="${sub%/}"
	echo "Working on $proteome_url"

	mapfile -t FILES < <(curl -fsSL "$proteome_url" | tr '""' '\n' | grep -E '^UP[0-9]{9}_[0-9]+\.(gene2acc)\.gz$' | sed -E 's/^href="(.*)"$/\1/' | sort -u)

	echo "N. files in current dir: ${#FILES[@]}"

	((${#FILES[@]}==0)) && continue

	downloaded_any=false
  	for fname in "${FILES[@]}"; do
    		# Strip any query string just in case (rare on FTP-style listings)
    		fname_clean="${fname%%\?*}"
    		outfile="${DOWNLOAD_DIR}/${fname_clean##*/}"

    		if [[ -s "$outfile" ]]; then
      			echo "   - exists, skipping: ${outfile##*/}"
      			downloaded_any=true
      			continue
    		fi

    		echo "   - downloading: ${outfile##*/}"
    		curl -fSL --retry 3 --retry-delay 2 -o "$outfile" "${proteome_url}${fname_clean}"
    		downloaded_any=true
  	done

	# Record subfolder name only if at least one file was downloaded or already present
	if [[ "$downloaded_any" == true ]]; then
		echo "$sub_name" >> "$LIST_FILE"
  	fi
done

# Deduplicate the list file
sort -u -o "$LIST_FILE" "$LIST_FILE"

echo
echo "Done."
echo "• Files saved in: $DOWNLOAD_DIR"
echo "• Fetched subfolders listed in: $LIST_FILE"
