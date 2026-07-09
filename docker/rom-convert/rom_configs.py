"""
Configuration settings for game console ROM conversions.
This maps system folders to their ideal compressed formats and extensions.
"""

SYSTEM_CONFIGS = {
    # ================================================================
    # --- Cartridge Based (LZMA2 Archive Compression) ---
    # ================================================================
    "nes": {
        "exts": {".nes"},
        "output_ext": ".7z",
        "format": "archive",
        "description": "Nintendo Entertainment System (1983)",
        "aliases": ["famicom"],
    },
    "megadrive": {
        "exts": {".md", ".gen", ".smd"},
        "output_ext": ".7z",
        "format": "archive",
        "description": "Sega Genesis / Mega Drive (1988)",
        "aliases": ["genesis"],
    },
    "snes": {
        "exts": {".sfc", ".smc"},
        "output_ext": ".7z",
        "format": "archive",
        "description": "Super Nintendo (1992)",
        "aliases": ["sfc"],
    },
    "n64": {
        "exts": {".n64", ".z64", ".v64"},
        "output_ext": ".7z",
        "format": "archive",
        "description": "Nintendo 64 (1996)",
        "aliases": [],
    },
    # ================================================================
    # --- CD/DVD Based Systems (Universal CHD Compression) ---
    # ================================================================
    "segacd": {
        "exts": {".cue", ".iso"},
        "output_ext": ".chd",
        "format": "chd",
        "description": "Sega CD (1992)",
        "aliases": ["megacd"],
    },
    "saturn": {
        "exts": {".cue", ".iso"},
        "output_ext": ".chd",
        "format": "chd",
        "description": "Sega Saturn (1995)",
        "aliases": [],
    },
    "psx": {
        "exts": {".iso", ".cue"},
        "output_ext": ".chd",
        "format": "chd",
        "description": "Sony PlayStation (1995)",
        "aliases": ["ps1"],
    },
    "dreamcast": {
        "exts": {".gdi", ".cue", ".iso"},
        "output_ext": ".chd",
        "format": "chd",
        "description": "Sega Dreamcast (1999)",
        "aliases": ["dc"],
    },
    "ps2": {
        "exts": {".iso", ".cue"},  # Omit .bin to force reading via .cue
        "output_ext": ".chd",
        "format": "chd",
        "description": "Sony PlayStation 2 (2000)",
        "aliases": [],
    },
    # ================================================================
    # --- Microsoft Optical (Stripped Zero-Padding) ---
    # ================================================================
    "xbox": {
        "exts": {".iso"},
        "output_ext": ".iso",
        "format": "rebuilt_iso",
        "description": "Xbox (2001)",
        "aliases": [],
    },
    "xbox360": {
        "exts": {".iso"},
        "output_ext": ".iso",
        "format": "rebuilt_iso",
        "description": "Xbox 360 (2005)",
        "aliases": [],
    },
    # ================================================================
    # --- Nintendo Optical (Proprietary Encryption, lossless junk stripping) ---
    # ================================================================
    "gc": {
        "exts": {".iso", ".gcm", ".ciso"},
        "output_ext": ".rvz",
        "format": "rvz",
        "description": "Nintendo GameCube (2001)",
        "aliases": ["gamecube"],
    },
    "wii": {
        "exts": {".iso", ".wbfs"},
        "output_ext": ".rvz",
        "format": "rvz",
        "description": "Nintendo Wii (2006)",
        "aliases": [],
    },
}
