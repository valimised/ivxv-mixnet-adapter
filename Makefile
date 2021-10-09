VER := $(shell head -n1 ../ivxv/debian/changelog | cut -d" " -f2 | sed "s/(//" | sed "s/)//" )

.PHONY: all
all: zip

.PHONY: zip
zip: releaseall
	cd release; zip -r ivxv-verificatum-$(VER)-runner.zip mixer/

.PHONY: zipext
zipext: releaseallext
	cd release; zip -r ivxv-verificatum-$(VER)-runner-with-verificatum.zip mixer/

.PHONY: releaseall
releaseall: releaseivxv releaseadapter releasetools

.PHONY: releaseallext
releaseallext: releaseall releaseverificatum

.PHONY: releaseadapter
releaseadapter: mkreleasedir lib/ivxv-verificatum-$(VER).jar
	cp lib/ivxv-verificatum-$(VER).jar release/mixer/lib/ivxv-verificatum.jar

.PHONY: releaseivxv
releaseivxv: mkreleasedir lib/ivxv-common-$(VER).jar lib/ivxv-common-$(VER)-all.jar
	cp lib/ivxv-common-$(VER).jar release/mixer/lib/ivxv-common.jar
	cp lib/ivxv-common-$(VER)-all.jar release/mixer/lib/ivxv-common-all.jar

.PHONY: releaseverificatum
releaseverificatum: mkreleasedir lib/libgmpmee.so.0.0.0 lib/verificatum-vmgj-1.2.2.jar lib/libvmgj-1.2.2.so lib/verificatum-vcr-vmgj-3.0.4.jar lib/verificatum-vmn-3.0.4.jar
	cp lib/verificatum-vmgj-1.2.2.jar release/mixer/lib/verificatum-vmgj.jar
	cp lib/verificatum-vcr-vmgj-3.0.4.jar release/mixer/lib/verificatum-vcr.jar
	cp lib/verificatum-vmn-3.0.4.jar release/mixer/lib/verificatum-vmn.jar
	cp lib/libgmpmee.so.0.0.0 release/mixer/lib/libgmpmee.so.0
	cp lib/libvmgj-1.2.2.so release/mixer/lib/libvmgj-1.2.2.so

.PHONY: releasetools
releasetools: mkreleasedir
	cp tools/mix.py tools/asn1.py tools/clean release/mixer/bin

lib/ivxv-version.gradle:
	echo "version \"$(VER)\"" > lib/ivxv-version.gradle

lib/ivxv-verificatum-$(VER).jar: lib/verificatum-vmn-3.0.4.jar lib/ivxv-common-$(VER).jar lib/ivxv-common-$(VER)-all.jar lib/ivxv-version.gradle
	../ivxv/common/external/gradle-6.4/bin/gradle jar
	cp build/libs/ivxv-verificatum-$(VER).jar lib/ivxv-verificatum-$(VER).jar

lib/ivxv-common-$(VER).jar:
	../ivxv/common/external/gradle-6.4/bin/gradle -b ../ivxv/common/java/build.gradle jar
	cp ../ivxv/common/java/build/libs/common-$(VER).jar lib/ivxv-common-$(VER).jar

lib/ivxv-common-$(VER)-all.jar:
	../ivxv/common/external/gradle-6.4/bin/gradle -b ../ivxv/common/java/build.gradle jarall
	cp ../ivxv/common/java/build/libs/common-$(VER)-all.jar lib/ivxv-common-$(VER)-all.jar

lib/libgmpmee.so.0.0.0:
	$(MAKE) -C ../verificatum-gmpmee -f Makefile.build
	cd ../verificatum-gmpmee/; ./configure --prefix=$(PWD)/../ivxv-verificatum/build/
	$(MAKE) -C ../verificatum-gmpmee
	$(MAKE) -C ../verificatum-gmpmee install
	cp build/lib/libgmpmee.so.0.0.0 lib/

lib/verificatum-vmgj-1.2.2.jar: lib/libgmpmee.so.0.0.0
	$(MAKE) -C ../vmgj -f Makefile.build
	cd ../vmgj/; CPPFLAGS="-I$(PWD)/../ivxv-verificatum/build/include" LDFLAGS="-L$(PWD)/../ivxv-verificatum/build/lib/" ./configure --prefix=$(PWD)/../ivxv-verificatum/build/
	$(MAKE) -C ../vmgj
	$(MAKE) -C ../vmgj install
	cp build/share/java/verificatum-vmgj-1.2.2.jar build/lib/libvmgj-1.2.2.so lib/

lib/libvmgj-1.2.2.so: lib/libgmpmee.so.0.0.0
	$(MAKE) -C ../vmgj -f Makefile.build
	cd ../vmgj/; CPPFLAGS="-I$(PWD)/../ivxv-verificatum/build/include" LDFLAGS="-L$(PWD)/../ivxv-verificatum/build/lib/" ./configure --prefix=$(PWD)/../ivxv-verificatum/build/
	$(MAKE) -C ../vmgj
	$(MAKE) -C ../vmgj install
	cp build/share/java/verificatum-vmgj-1.2.2.jar build/lib/libvmgj-1.2.2.so lib/

lib/verificatum-vcr-vmgj-3.0.4.jar: lib/verificatum-vmgj-1.2.2.jar
	$(MAKE) -C ../vcr -f Makefile.build
	cd ../vcr/; LD_LIBRARY_PATH=$(PWD)/../ivxv-verificatum/build/lib/ VMGJ_INFO=$(PWD)/../ivxv-verificatum/build/bin/vmgj-1.2.2-info ./configure --enable-vmgj --prefix=$(PWD)/../ivxv-verificatum/build/
	$(MAKE) -C ../vcr
	$(MAKE) -C ../vcr install
	cp build/share/java/verificatum-vcr-vmgj-3.0.4.jar lib/

lib/verificatum-vmn-3.0.4.jar: lib/verificatum-vcr-vmgj-3.0.4.jar
	$(MAKE) -C ../vmn -f Makefile.build
	cd ../vmn/; PATH=$(PATH):$(PWD)/../ivxv-verificatum/build/bin/ ./configure --prefix=$(PWD)/../ivxv-verificatum/build/
	$(MAKE) -C ../vmn
	$(MAKE) -C ../vmn install
	cp build/share/java/verificatum-vmn-3.0.4.jar lib/

.PHONY: mkreleasedir
mkreleasedir:
	mkdir -p release/mixer/lib
	mkdir -p release/mixer/bin

.PHONY: clean
clean:
	rm -rf release
	rm -rf build
	rm -f lib/verificatum-vmgj-1.2.2.jar
	rm -f lib/verificatum-vcr-vmgj-3.0.4.jar
	rm -f lib/verificatum-vmn-3.0.4.jar
	rm -f lib/ivxv-common-$(VER).jar
	rm -f lib/ivxv-common-$(VER)-all.jar
	rm -f lib/libgmpmee.so.0.0.0
	rm -f lib/libvmgj-1.2.2.so
	rm -f lib/ivxv-verificatum-$(VER).jar
	../ivxv/common/external/gradle-6.4/bin/gradle clean
	rm -f lib/ivxv-version.gradle
	$(MAKE) -C ../vmn clean
	$(MAKE) -C ../vmn -f Makefile.build clean
	$(MAKE) -C ../vcr clean
	$(MAKE) -C ../vcr -f Makefile.build clean
	$(MAKE) -C ../vmgj clean
	$(MAKE) -C ../vmgj -f Makefile.build clean
	$(MAKE) -C ../verificatum-gmpmee clean
	$(MAKE) -C ../verificatum-gmpmee -f Makefile.build clean
