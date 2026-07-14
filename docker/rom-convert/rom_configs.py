"""
Configuration settings for game console ROM conversions.
This maps system folders to their ideal compressed formats and extensions.
"""

SYSTEM_CONFIGS = {
    # ================================================================
    # --- Cartridge Based (LZMA2 Archive Compression) ---
    # ================================================================
    "nes": {
        "exts": {".nes", ".fds", ".unf", ".unif", ".zip", ".rar", ".7z"},
        "output_ext": ".7z",
        "format": "archive",
        "description": "Nintendo Entertainment System (1983)",
        "aliases": ["famicom"],
    },
    "megadrive": {
        "exts": {
            ".md",
            ".gen",
            ".smd",
            ".bin",
            ".32x",
            ".sms",
            ".gg",
            ".sg",
            ".zip",
            ".rar",
            ".7z",
        },
        "output_ext": ".7z",
        "format": "archive",
        "description": "Sega Genesis / Mega Drive / 32X (1988)",
        "aliases": ["genesis", "sega32x"],
    },
    "snes": {
        "exts": {".sfc", ".smc", ".bs", ".st", ".fig", ".swc", ".zip", ".rar", ".7z"},
        "output_ext": ".7z",
        "format": "archive",
        "description": "Super Nintendo (1992)",
        "aliases": ["sfc"],
    },
    "n64": {
        "exts": {".n64", ".z64", ".v64", ".ndd", ".zip", ".rar", ".7z"},
        "output_ext": ".7z",
        "format": "archive",
        "description": "Nintendo 64 (1996)",
        "aliases": [],
    },
    # ================================================================
    # --- CD/DVD Based Systems (Universal CHD Compression) ---
    # NOTE: Raw payload files (.bin, .raw, .img) are intentionally omitted.
    # By targeting only the descriptor files (.cue, .gdi, .ccd, .m3u), it guarantees
    # multi-track games aren't accidentally split into separated, corrupted conversions.
    # ================================================================
    "segacd": {
        "exts": {".cue", ".iso", ".chd"},
        "output_ext": ".chd",
        "format": "chd",
        "description": "Sega CD (1992)",
        "aliases": ["megacd"],
    },
    "saturn": {
        "exts": {".cue", ".iso", ".chd", ".m3u"},
        "output_ext": ".chd",
        "format": "chd",
        "description": "Sega Saturn (1995)",
        "aliases": [],
    },
    "psx": {
        "exts": {".cue", ".iso", ".ccd", ".m3u", ".chd"},
        "output_ext": ".chd",
        "format": "chd",
        "description": "Sony PlayStation (1995)",
        "aliases": ["ps1", "psx"],
    },
    "dreamcast": {
        "exts": {".gdi", ".cue", ".iso", ".cdi", ".chd"},
        "output_ext": ".chd",
        "format": "chd",
        "description": "Sega Dreamcast (1999)",
        "aliases": ["dc"],
    },
    "ps2": {
        "exts": {".cue", ".iso", ".m3u", ".chd"},
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
        "exts": {".iso", ".gcm", ".ciso", ".gcz", ".nkit.iso", ".wbfs", ".rvz"},
        "output_ext": ".rvz",
        "format": "rvz",
        "description": "Nintendo GameCube (2001)",
        "aliases": ["gamecube"],
    },
    "wii": {
        "exts": {".iso", ".wbfs", ".ciso", ".gcz", ".nkit.iso", ".wdf", ".rvz"},
        "output_ext": ".rvz",
        "format": "rvz",
        "description": "Nintendo Wii (2006)",
        "aliases": [],
    },
}
