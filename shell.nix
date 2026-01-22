{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    python3
    python3Packages.pip
    python3Packages.virtualenv
    
    # C/C++ kütüphaneleri (numpy, pandas için gerekli)
    stdenv.cc.cc.lib
    zlib
    glib
    
    # Ek bağımlılıklar
    libffi
    openssl
  ];

  shellHook = ''
    export LD_LIBRARY_PATH="${pkgs.lib.makeLibraryPath [
      pkgs.stdenv.cc.cc.lib
      pkgs.zlib
      pkgs.glib
      pkgs.libffi
      pkgs.openssl
    ]}:$LD_LIBRARY_PATH"
    
    # Virtualenv oluşturma (eğer yoksa)
    if [ ! -d "venv" ]; then
      echo "Creating virtual environment..."
      python -m virtualenv venv
    fi
    
    echo "Activating virtual environment..."
    source venv/bin/activate
    
    echo "Virtual environment is ready!"
    echo "Install packages with: pip install streamlit pandas numpy ccxt"
  '';
}