{ pkgs ? import <nixpkgs> {} }:

# System packages needed to run tests with Qt, which requires
let
  libs = with pkgs; [
    # OpenGL
    libGL
    libglvnd

    # Fonts & text
    fontconfig
    freetype

    # System
    dbus
    glib
    zlib
    stdenv.cc.cc.lib

    # X11 / Qt platform (top-level names since the xorg package set was deprecated)
    libx11
    libxext
    libxrender
    libxrandr
    libxi
    libxcursor
    libxfixes
    libxcomposite
    libxdamage
    libxcb
    libxcb-cursor
    libxcb-image
    libxcb-keysyms
    libxcb-render-util
    libxcb-wm
    libxkbcommon
  ];
in
pkgs.mkShell {
  packages = with pkgs; [
    uv
    python311
    go-task

    # Include qttools for lrelease, lupdate commands
    qt6.qttools
  ];

  LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath libs;

  shellHook = ''
    # Headless Qt for unit tests (no display needed)
    export QT_QPA_PLATFORM=offscreen
  '';
}
