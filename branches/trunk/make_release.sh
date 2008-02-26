#!/bin/bash
# Script to make an official release of blueproximity
# (c) 2007 Lars Friedrichs
#
# configure base variables
VERSION=1.2.5
VNAME=`pwd`
DNAME=$VNAME-$VERSION
DISTRIB=hardy
export DEBFULLNAME="Lars Friedrichs"
#export DEBFULLNAME="Lars Friedrichs (Quattro-Scan GmbH)"
export NAME=$DEBFULLNAME
export DEBEMAIL="LarsFriedrichs@gmx.de"
#export DEBEMAIL="l.friedrichs@qs.nitag.de"
export EMAIL=$DEBEMAIL

. /etc/lsb-release

# build the source tar-ball
echo First we create the locales
./create_translation.sh
echo Now building the source tar-ball
cd ..
mkdir $DNAME
echo . copying everything in place
cp $VNAME/proximity.glade $DNAME
#cp $VNAME/proximity.gladep $DNAME
cp $VNAME/proximity.py $DNAME
cp $VNAME/start_proximity.sh $DNAME
cp $VNAME/bluepro*.svg $DNAME
cp -r $VNAME/LANG $DNAME
cp $VNAME/COPYING $DNAME
cp $VNAME/README $DNAME
cp $VNAME/ChangeLog $DNAME
cp -r $VNAME/debian-addons $DNAME/addons
cp -r $VNAME/doc $DNAME

echo . deleting subversion files
find $DNAME -iname .svn -exec rm -rf \{\} \;

echo . creating the .tar.gz file
rm $VNAME/$DNAME.tar.gz 2> /dev/null
tar czf $VNAME/$DNAME.tar.gz $DNAME

echo . removing temporary files
rm -Rf $DNAME
echo Done.

# now build the ubuntu package
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

#step is done via patches
#echo . copying package addons
#cp $VNAME/debian-addons/* $DNAME

echo . deleting subversion files
find $DNAME -iname .svn -exec rm -rf \{\} \;

#echo . modify source for packaging
#rm $DNAME/start_proximity.sh
#cat $DNAME/proximity.py | sed -e "s#dist_path = './'#dist_path = '/usr/share/blueproximity/'#" > $DNAME/proximity2.py
#mv -f $DNAME/proximity2.py $DNAME/proximity.py
chmod 755 $DNAME/proximity.py

# now make a debian changelog entry for the new upstream version
echo . now creating the debian changelog...
cd $DNAME
#STARTED=0
#DCH_OPTS="-a -v $VERSION-0ubuntu1 -D $DISTRIB"
DCH_OPTS="-a"
#cat CHANGELOG.txt |
#while read LINE
#do
#    FIRST_CHAR=`echo $LINE | cut -b 1`
#    if [ "$STARTED" == "0" ]; then
#        if [ "$FIRST_CHAR" == "-" ]; then
#            STARTED='1'
#        fi
#    fi
#    if [ "$STARTED" == "1" ]; then
#        if [ "$FIRST_CHAR" != "-" ]; then
#            STARTED='2'
#        fi
#    fi
#    if [ "$STARTED" == "1" ]; then
#	LOG_LINE=`echo $LINE | sed -e 's/^- //g'`
#	echo .. $LOG_LINE
#        dch $DCH_OPTS $LOG_LINE
#        DCH_OPTS=-a
#    fi
#done
dch $DCH_OPTS "New upstream version $VERSION packaged"
cd ..

echo . creating .deb file with debuild
cd $DNAME
echo ". we use debuild. If $DISTRIB is not your distribution you should also use pbuilder/pdebuild."
debuild

echo ". and now we create a source package for upload at REVU."
debuild -S -sa

cd ..
echo Done.

echo . copying the new debian-filestructure
#cp -rf $DNAME/debian $VNAME/debian-after-$VERSION

echo . cleaning up
#rm -rf $DNAME

echo All done.
echo You can now 
echo .  cd ..
echo .  dput $DNAME-0ubuntu1_source.changes
echo to upload the package to REVU
