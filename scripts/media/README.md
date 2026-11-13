## PNG to JPEG

`png-to-jpeg` converts PNG images in the current directory **and subdirectories**
using FFmpeg, then moves each original into a `PNG/` folder beside that image.
It preserves dimensions, composites transparency over white, and defaults to
high-quality JPEG (`-q:v 2`, 4:4:4 color). JPEG is lossy and is not always smaller;
originals are retained unchanged. Keeping originals also means total disk usage
increases. Metadata and color profiles are not guaranteed to survive conversion;
animated PNGs produce a JPEG of their first frame only.

Requires Python 3.8+ and `ffmpeg` on PATH; supports Linux and macOS. Install FFmpeg
with your system's package manager if needed. No Python packages are required.

From your dotfiles checkout, install the command once (an existing destination
will not be overwritten):

```sh
mkdir -p "$HOME/.local/bin"
ln -s "$PWD/bin/png-to-jpeg" "$HOME/.local/bin/png-to-jpeg"
export PATH="$HOME/.local/bin:$PATH"
```

Add the `export PATH` line to your `~/.bashrc` or `~/.zshrc` if it is not already
configured. Then run from any image directory:

```sh
png-to-jpeg --dry-run          # preview conversion and original destinations
png-to-jpeg                    # convert this directory and subdirectories
png-to-jpeg --no-recursive     # only this directory
png-to-jpeg --quality 4        # smaller files, more compression (1–31; lower is better)
png-to-jpeg /path/to/images    # optionally specify a directory
png-to-jpeg --help
```

Matching is case-insensitive for `.png` extensions and includes hidden files.
Archive directories named `PNG` (any capitalization) and symlinks are excluded
from recursive scans. Existing JPEG names or archived originals are skipped;
files are never overwritten. Each JPEG is decoded to check it before its original
is moved. Failures leave originals in place, are reported, and produce a nonzero
exit status while other images continue. The filesystem must support hard links
for safe publication and archival without overwriting files.

## Video to GIF

`video-to-gif` converts one MOV, MP4, or other FFmpeg-readable video into a looping
GIF for app demos. Defaults: maximum width **960 pixels**, **10 fps**, full video
duration, and output beside the source with a `.gif` extension. It preserves the
display aspect ratio without upscaling and honors video rotation metadata.
Sources stay unchanged; existing outputs are refused. Requires Python 3.8+ and
`ffmpeg` on PATH on Linux/macOS, with no additional Python packages.

Install once from your dotfiles checkout:

```sh
mkdir -p "$HOME/.local/bin"
ln -s "$PWD/bin/video-to-gif" "$HOME/.local/bin/video-to-gif"
export PATH="$HOME/.local/bin:$PATH"
```

Keep the PATH line in your `~/.bashrc` or `~/.zshrc` if not already configured.
Then run from wherever your recordings are stored:

```sh
video-to-gif "Screen Recording.mov"
video-to-gif demo.mp4 --start 2.5 --duration 8 -o feature-demo.gif
video-to-gif demo.mov --width 720 --fps 8  # reduce size
video-to-gif demo.mov --dry-run           # show commands without writing files
video-to-gif --help
```

`--start` and `--duration` accept seconds, including decimals. Duration is measured
from the start offset. To use an input filename beginning with `-`, place `--`
before its name. Custom output directories must already exist.

Conversion uses two FFmpeg passes to generate and apply a color palette, then
decodes the GIF to verify it before publishing. Temporary files are created beside
the output and cleaned up on success or failure. Safe publication requires a
filesystem with hard-link support. GIFs loop continuously, have no audio, and
have limited colors; gradients and fine text may lose detail. Size depends on the
recording; trimming duration usually helps most, followed by reducing width or fps.
No upload-size limit is enforced. Upload the resulting GIF as an attachment in
your pull request or Confluence page; the command performs no uploads.
## Browser-compatible MP4

`video-to-mp4` converts legacy videos for browser playback through copyparty.
Run it without arguments to process the current directory, or pass one file.
Default output is `NAME.web.mp4` beside the source. Originals stay unchanged.
Existing destinations are skipped, and directory scans ignore generated
`*.web.mp4` files and symlinks. Use `--recursive` to include subdirectories.

Requires Python 3.8+, FFmpeg with `libx264` and AAC encoding, and `ffprobe`.
CPU conversion supports Linux and macOS. No Python packages are required.
Install the command once from your dotfiles checkout:

```sh
mkdir -p "$HOME/.local/bin"
ln -s "$PWD/bin/video-to-mp4" "$HOME/.local/bin/video-to-mp4"
export PATH="$HOME/.local/bin:$PATH"
```

Keep the PATH line in `~/.bashrc` or `~/.zshrc` if not already configured.
Then run from any directory:

```sh
video-to-mp4                          # current directory, CPU encoding
video-to-mp4 "old recording.wmv"      # one file -> old recording.web.mp4
video-to-mp4 /path/to/videos -r       # include subdirectories
video-to-mp4 --dry-run               # inspect streams and preview commands
video-to-mp4 movie.avi -o movie.mp4   # choose an unused output filename
video-to-mp4 movie.flv -q 18 --preset slow
video-to-mp4 movie.webm --encoder nvidia
video-to-mp4 movie.wmv --encoder amd
video-to-mp4 movie.avi --deinterlace
video-to-mp4 --help
```

Directory scans match FLV, WebM, AVI, WMV, ASF, WMA, MP4, M4V, MOV, MKV, MPG,
MPEG, VOB, 3GP, TS, M2TS, and OGV, case-insensitively. An explicitly supplied file
can have any extension FFmpeg recognizes. Files sharing a stem share a default
output name: the first successful conversion wins, and subsequent collisions are
skipped. Use `--output` individually to retain both. For names starting with `-`,
use `--` before the input filename.

### Output and quality

Outputs contain 8-bit H.264 High profile video with 4:2:0 chroma and stereo AAC-LC
audio at 160 kbps/48 kHz. MP4 metadata is moved to the beginning (`+faststart`) so
playback can start before the complete file downloads. The first non-cover-art
video stream and first audio stream are selected; subtitles, other tracks,
chapters, and source metadata are omitted. Silent videos remain silent;
audio-only inputs produce audio-only AAC MP4s. WMV is Windows Media Video, while
WMA is normally Windows Media Audio; actual streams determine the conversion.

Even video dimensions stay unchanged. Odd dimensions round up by one pixel to
meet 4:2:0 requirements; sample aspect ratio is adjusted to preserve the display
aspect ratio. FFmpeg honors rotation metadata. Frame timing is passed through
without forcing a fixed frame rate. `--deinterlace` applies BWDIF at the original
frame rate; enable it for interlaced footage that shows combing artifacts.

CPU defaults are `libx264`, CRF 20, and the `medium` preset. `--quality 1–51`
controls quality (lower means better/larger); `--preset slow` trades CPU time for
compression efficiency. `--audio-bitrate 192` changes the stereo bitrate in kbps.
GPU quality uses NVENC CQ or VA-API QP; these numbers are not directly equivalent
to CPU CRF. All modes re-encode and are lossy; file size may increase. This tool
targets SDR recordings and rejects detected HDR inputs rather than producing an
incorrect SDR conversion. It does not downscale very large videos to meet older
device limits, and cannot guarantee playback on every browser/device.

### Linux GPU encoding

`--encoder nvidia` uses `h264_nvenc` with the `p5` preset and VBR/CQ quality.
It requires an NVIDIA GPU with H.264 encoding, a working NVIDIA driver, and an
FFmpeg build with NVENC support. `--device 0` selects a specific GPU index;
otherwise FFmpeg selects an available device.

`--encoder amd` uses `h264_vaapi` with constant-QP quality. It detects an AMD
render node using Linux sysfs vendor IDs. The GPU/driver must support H.264
encoding through VA-API, and your user must have access to the render device.
Use `--device /dev/dri/renderD129` to select an AMD device explicitly. Containers
also need access to the GPU device and matching runtime/driver libraries.

Both GPU modes decode/filter on the CPU and accelerate encoding only, allowing
legacy input codecs that GPUs may not decode. A short encode checks hardware
availability before processing video. Failure is reported with no silent switch
to CPU; rerun with `--encoder cpu` if needed. Dry runs detect the AMD device but
do not initialize or test GPU encoders. `--preset` is CPU-only.

### Safety and serving

Each conversion uses temporary storage beside its destination. The result is
probed for expected codecs and fully decoded before it is published without
overwriting an existing file. This verification adds a decoding pass. Publication
requires hard-link support on the destination filesystem. Errors leave originals
unchanged, temporary files are cleaned up, and batch processing continues after
individual file failures with a nonzero final exit status. An encoder availability
failure stops the run. Interrupted runs may leave temporary directories after a
forced kill; directory scans exclude those directories.

Place the resulting `.web.mp4` files in the directory served by copyparty, or run
the converter there. The command does not upload files or change server settings.
Test a representative converted video in your target browser before converting a
large collection. MP4 container support alone is insufficient; the codecs inside
must also be supported ([copyparty discussion](https://github.com/9001/copyparty/issues/210)).
See [FFmpeg's encoder documentation](https://ffmpeg.org/ffmpeg-codecs.html) for
hardware encoder requirements and options.
