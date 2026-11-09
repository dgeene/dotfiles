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
