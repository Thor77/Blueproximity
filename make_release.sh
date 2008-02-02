#!/bin/bash
# Script to make an official release of blueproximity
# (c) 2007 Lars Friedrichs
#
# configure base variables
VERSION=1.2.2
VNAME=blueproximity
DNAME=$VNAME-$VERSION
export DEBFULLNAME="Lars Friedrichs"
export NAME=$DEBFULLNAME
export DEBEMAIL="LarsFriedrichs@gmx.de"
export EMAIL=$DEBEMAIL

# build the source tar-ball
echo First we create the locales
./create_translation.sh
echo Now building the source tar-ball
cd ..
mkdir $DNAME
echo . copying everything in place
cp $VNAME/proximity.glade $DNAME
cp $VNAME/proximity.gladep $DNAME
cp $VNAME/proximity.py $DNAME
cp $VNAME/start_proximity.sh $DNAME
cp $VNAME/bluepro*.svg $DNAME
cp -r $VNAME/LANG $DNAME
cp $VNAME/README.txt $DNAME
cp $VNAME/CHANGELOG.txt $DNAME
cp -r $VNAME/doc $DNAME

echo . creating the .tar.gz file
rm $VNAME/$DNAME.tar.gz 2> /dev/null
tar czf $VNAME/$DNAME.tar.gz $DNAME

echo . removing temporary files
rm -Rf $DNAME
echo Done.

# now build the debian/ubuntu package
echo Now building the .deb package
echo . unpacking the source
tar xzf $VNAME/$DNAME.tar.gz

echo . creating the .deb infrastructure
cd $DNAME
dh_make -c gpl -b --createorig
cd ..
rm -r $DNAME/debian

echo . copying our preset debian dir
cp -r $VNAME/debian $DNAME

echo . copying package addons
cp $VNAME/debian-addons/* $DNAME

echo . modify source for packaging
rm $DNAME/start_proximity.sh
cat $DNAME/proximity.py | sed -e "s#dist_path = './'#dist_path = '/usr/share/blueproximity/'#" > $DNAME/proximity2.py
mv -f $DNAME/proximity2.py $DNAME/proximity.py
chmod 755 $DNAME/proximity.py

# now make a debian changelog from ours
echo . now creating the debian changelog...
cd $DNAME
STARTED=0
DCH_OPTS="-p -v $VERSION"
cat CHANGELOG.txt |
while read LINE
do
    FIRST_CHAR=`echo $LINE | cut -b 1`
    if [ "$STARTED" == "0" ]; then
        if [ "$FIRST_CHAR" == "-" ]; then
            STARTED='1'
        fi
    fi
    if [ "$STARTED" == "1" ]; then
        if [ "$FIRST_CHAR" != "-" ]; then
            STARTED='2'
        fi
    fi
    if [ "$STARTED" == "1" ]; then
	LOG_LINE=`echo $LINE | sed -e 's/^- //g'`
	echo .. $LOG_LINE
        dch $DCH_OPTS $LOG_LINE
        DCH_OPTS=-a
    fi
done
cd ..

echo . creating .deb file with debuild
cd $DNAME
debuild
cd ..
echo Done.

echo . copying the new debian-filestructure
cp -rf $DNAME/debian $VNAME/debian-after-$VERSION

echo . cleaning up
rm -rf $DNAME

echo All done.
