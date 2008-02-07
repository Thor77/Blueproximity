#!/bin/bash
#LANGS="de en es fr fa sv"
LANGS="de en es fa it"

function create_mo() {
  mkdir -p LANG/$1/LC_MESSAGES
  msgfmt --output-file=LANG/$1/LC_MESSAGES/blueproximity.mo $1.po
}

rm -rf LANG

for lang in $LANGS; do
    create_mo $lang
    echo "$lang locale created"
done
