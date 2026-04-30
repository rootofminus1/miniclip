sudo docker run --rm -v $PWD:/host amazonlinux:2 bash -c "
  yum groupinstall -y 'Development Tools' && \
  yum install -y autoconf automake libtool pkgconfig git wget xz tar make nasm zlib-devel && \
  mkdir -p /tmp/layer/bin /tmp/ffmpeg && cd /tmp/ffmpeg && \
  git clone --depth 1 --branch n7.1 https://git.ffmpeg.org/ffmpeg.git ffmpeg && cd ffmpeg && \
  ./configure \
    --prefix=/tmp/layer \
    --disable-debug \
    --disable-doc \
    --disable-ffplay \
    --enable-small \
    --enable-static \
    --disable-shared && \
  make -j\$(nproc) && make install && \
  strip --strip-all /tmp/layer/bin/ffmpeg /tmp/layer/bin/ffprobe && \
  cd /tmp/layer && zip -9 -r /host/ffmpeg-layer.zip bin
"