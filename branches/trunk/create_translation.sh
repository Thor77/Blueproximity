#!/bin/bash
#LANGS="de en es fa fr hu it ru sv th"
LANGS="de en fr hu it"

function create_mo() {
  mkdir -p LANG/$1/LC_MESSAGES
  msgfmt --output-file=LANG/$1/LC_MESSAGES/blueproximity.mo po/$1.po
}

rm -rf LANG

for lang in $LANGS; do
    create_mo $lang
    echo "$lang locale created"
done
