# Installing T2GD

T2GD ships as a prebuilt binary. There is nothing to compile, nothing to
install and no dependency to resolve for command line use. Download the
archive for your platform, unpack it, and run it.

The manual is compiled into the executable, so `t2gd-cli help` works
immediately on a machine with no network and nothing on the path.

## Choose an archive

All five archives are attached to the
[v1.19.0 release](https://github.com/Arnaroo/T2GD/releases/tag/v1.19.0).

| Archive | Platform | Requirement |
|---|---|---|
| `t2gd-1.19.0-Shenlong-linux-x86_64-broadwell.tar.gz` | Linux x86_64 | any reasonably modern x86_64, the safe default |
| `t2gd-1.19.0-Shenlong-linux-x86_64-znver2.tar.gz` | Linux x86_64 | AMD Zen 2 or newer |
| `t2gd-1.19.0-Shenlong-linux-x86_64-znver4.tar.gz` | Linux x86_64 | AVX-512, so AMD Zen 4 or newer |
| `t2gd-1.19.0-Shenlong-macos-arm64.tar.gz` | macOS | Apple Silicon M1 or newer, macOS 14 or newer |
| `t2gd-1.19.0-Shenlong-windows-x86_64.zip` | Windows | any x86-64, Windows 10 or newer |

**Which Linux build?** If you are not sure, take **broadwell**. It runs
everywhere the other two do. The znver2 and znver4 builds are tuned for
those microarchitectures; znver4 contains AVX-512 instructions and will
fault with an illegal instruction on a CPU without them. To check:

```sh
grep -o 'avx512[a-z]*' /proc/cpuinfo | sort -u | head
```

Output means znver4 will run. No output means use broadwell or znver2.

There is no Intel Mac build, no universal binary, no 32-bit build and no
Linux arm64 build.

## Which binary is in the archive

The Linux and macOS archives contain two executables:

* **`t2gd`** is the full build. Run it with no arguments and the graphical
  interface opens; put `--cli` in front of a subcommand and it runs
  headless. It needs the GTK 3 runtime present and discoverable, because
  the toolkit is loaded at startup rather than linked, and that applies
  even when you use it headless.
* **`t2gd-cli`** contains no graphical code at all and needs nothing beyond
  the platform system libraries. This is the binary for HPC nodes,
  containers, and any command line work.

The Windows archive contains **two** executables as well, for a different
reason. `t2gd.exe` is the graphical interface and `t2gd-cli.exe` is the
command line. The split is not about GTK, since the GTK 3 runtime travels
inside the Windows bundle either way. It is about the console. A Windows
program declares at link time whether it owns a console window, and it cannot
answer both ways. `t2gd.exe` answers "no", so double-clicking it opens the GUI
clean with no empty black console behind it, and `t2gd-cli.exe` answers "yes"
so that command line work has somewhere to print.

## Linux

```sh
tar xzf t2gd-1.19.0-Shenlong-linux-x86_64-broadwell.tar.gz
cd linux-broadwell
sha256sum -c SHA256SUMS
chmod +x t2gd t2gd-cli
./t2gd-cli --version
```

Put it somewhere on your path if you want it available everywhere:

```sh
sudo install -m 755 t2gd-cli /usr/local/bin/
sudo install -m 755 t2gd     /usr/local/bin/
```

Or, without root:

```sh
mkdir -p ~/.local/bin && install -m 755 t2gd-cli ~/.local/bin/
```

Both binaries are static beyond the platform C libraries. `readelf -d`
NEEDED lists only `libz.so.1`, `libm.so.6`, `libgcc_s.so.1`, `libc.so.6`
and `ld-linux-x86-64.so.2`. GTK 3 is absent from that list even in the
full build.

**For the graphical interface**, install GTK 3 from your distribution:

```sh
sudo apt install libgtk-3-0        # Debian, Ubuntu
sudo dnf install gtk3              # Fedora
sudo pacman -S gtk3                # Arch, Manjaro
```

Then run `./t2gd`. If GTK is missing, `t2gd` exits at startup with a
dynamic loader error naming a GTK library. That is expected and is not a
fault in the binary; use `t2gd-cli` for command line work.

## macOS

```sh
tar xzf t2gd-1.19.0-Shenlong-macos-arm64.tar.gz
cd macos-arm64
shasum -a 256 -c SHA256SUMS
xattr -dr com.apple.quarantine T2GD.app t2gd t2gd-cli
chmod +x t2gd t2gd-cli
./t2gd-cli --version
```

The archive contains three things: `T2GD.app` for the graphical interface,
`t2gd` which is the same GUI build as a bare executable, and `t2gd-cli` for
the command line.

Everything is ad-hoc signed rather than Developer ID notarised, so on first
run macOS quarantines it. The `xattr` line above clears the flag. Verify the
checksums before you clear it if you prefer.

**Use `T2GD.app`, not the bare `t2gd`, for the interface.** Drag it to
`/Applications` and open it from there. Finder does not launch a bare
executable directly. It hands it to Terminal, which opens a window and runs
the program inside it, so double-clicking `t2gd` gets you the interface with
a terminal welded to it. The bundle launches through the normal path and
opens on its own.

Both binaries are static beyond the system libraries. `otool -L` lists only
`libz`, `libSystem` and `libobjc`, all from `/usr/lib`. No Homebrew path is
baked into either binary and there is no `LC_RPATH`, so they run wherever
you put them.

**For the graphical interface** you must install GTK 3. macOS has no system
wide library search path that finds Homebrew, so `dyld` cannot locate GTK on
its own.

```sh
brew install gtk+3
```

That is all `T2GD.app` needs. The bundle looks in `/opt/homebrew/lib` and
`/usr/local/lib` itself and puts up a dialog if GTK is absent. It has to,
because a bundle launched from Finder inherits the launchd environment rather
than your shell's, so an export in your profile never reaches it, and with no
terminal attached a loader error would go nowhere you could see it.

Running the bare `t2gd` from a shell is the case where you point the loader
yourself, or it exits with `Library load failed (libatk-1.0.0.dylib)`:

```sh
export DYLD_LIBRARY_PATH=/opt/homebrew/lib
./t2gd
```

**On macOS, use `t2gd-cli` for all command line work.** The same GTK
requirement applies to `t2gd --cli`, because the toolkit is loaded before
the subcommand is dispatched. `t2gd-cli` has no graphical code in it and
needs none of this.

## Windows

Unpack the ZIP and **keep the whole folder together**. `t2gd.exe` finds its
GTK DLLs, the gdk-pixbuf loaders under `lib\` and the themes and icons
under `share\` by sitting next to them. Windows searches the executable's
own directory first, which is why nothing needs installing and no
environment variable is required. Moving `t2gd.exe` out on its own breaks
the graphical interface.

Double-click `t2gd.exe` for the graphical interface. It opens on its own,
with no console window beside it.

For the command line use `t2gd-cli.exe`:

```
t2gd-cli.exe --version
t2gd-cli.exe help
t2gd-cli.exe convert -g annotation.gtf -i tx.bam -o genome.bam -t 8
```

**Use `t2gd-cli.exe`, not `t2gd.exe --cli`.** Both accept the same
subcommands, but `t2gd.exe` is linked as a Windows-subsystem program and a
Windows-subsystem program is not given a console, so it has nowhere to print
to. `t2gd.exe --cli --version` will appear to do nothing at all. That is the
cost of removing the stray console window, and it is why the second binary
exists. Redirection is unaffected, because a redirected handle is inherited
from the shell rather than allocated by the program, so
`t2gd.exe --cli --version > out.txt` does write the file. But there is no
reason to rely on that when `t2gd-cli.exe` is sitting in the same folder.

`t2gd-cli.exe` is static beyond the Windows system libraries. Its import
table lists only `KERNEL32.dll`, `ADVAPI32.dll` and `WS2_32.dll`. The D
runtime, libdeflate and zlib are all linked in, so nothing in the bundled
DLL set is needed for command line work: `t2gd-cli.exe` runs on its own
even if you move it out of the folder. The DLLs, `lib\` and `share\` are
there for the graphical interface only.

**SmartScreen.** The executable is unsigned, so on first run Windows shows
"Windows protected your PC". Choose **More info**, then **Run anyway**.
Verify the download against `SHA256SUMS` first if you prefer:

```
certutil -hashfile t2gd.exe SHA256
```

or, in PowerShell:

```
Get-FileHash t2gd.exe -Algorithm SHA256
```

## Containers and HPC

`t2gd-cli` is the binary to use. Copy it into an image and it works; there
is nothing to install alongside it.

```dockerfile
FROM debian:bookworm-slim
COPY t2gd-cli /usr/local/bin/t2gd-cli
```

The manual, all fourteen topics and all twenty figures, is compiled into
the executable, so `t2gd-cli help` works inside a scratch-adjacent image
with no data directory and no network.

## Verifying a download

Each archive contains a `SHA256SUMS` covering the binaries and the shipped
documents. Checksums for the archives themselves are published with the
release as `SHA256SUMS`.

```sh
sha256sum -c SHA256SUMS         # Linux, both levels
shasum -a 256 -c SHA256SUMS     # macOS
```

## Confirming the install

```sh
t2gd-cli --version    # banner reads 1.19.0 / Shenlong
t2gd-cli help         # the topic index
```

For a first end to end run, see [USAGE.md](USAGE.md).

## A note on the built-in manual

`t2gd-cli help install` covers the same ground from inside the binary: the
same three Linux variants, the same two binaries per platform, the same
`T2GD.app`. Where the two differ in emphasis, this file is written from the
artifacts and is the one to trust.
