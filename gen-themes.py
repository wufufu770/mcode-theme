#!/usr/bin/env python3
"""生成 mcode 主题 JSON（知名 VS Code/终端主题色板）"""
import json, os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "themes")
os.makedirs(OUT, exist_ok=True)

UI_KEYS = ["brand","wordmarkHighlight","wordmarkShadow","signal","orbit",
           "accent","userMessageBg","text","muted","dim","border","line",
           "success","warning","error"]
SYN_KEYS = ["blue","flamingo","green","mauve","overlay2","peach","pink",
            "red","sapphire","subtext0","teal","text","yellow"]

DEFAULT_ANSI = {
    "brand":"cyanBright","wordmarkHighlight":"whiteBright","wordmarkShadow":"cyan",
    "signal":"cyanBright","orbit":"cyan","accent":"cyanBright",
    "text":"whiteBright","muted":"white","dim":"gray","border":"gray","line":"gray",
    "success":"greenBright","warning":"yellowBright","error":"redBright",
}

# 主题色板: name -> (bg, fg, accent, palette)
THEMES = {
    "dracula": dict(
        bg="#282A36", fg="#F8F8F2",
        accent="#BD93F9", orbit="#FF79C6",
        blue="#6272A4", cyan="#8BE9FD", green="#50FA7B", red="#FF5555",
        yellow="#F1FA8C", purple="#BD93F9", pink="#FF79C6", orange="#FFB86C",
    ),
    "nord": dict(
        bg="#2E3440", fg="#D8DEE9",
        accent="#88C0D0", orbit="#8FBCBB",
        blue="#5E81AC", cyan="#88C0D0", green="#A3BE8C", red="#BF616A",
        yellow="#EBCB8B", purple="#B48EAD", pink="#D08770", orange="#D08770",
    ),
    "solarized-dark": dict(
        bg="#002B36", fg="#839496",
        accent="#268BD2", orbit="#2AA198",
        blue="#268BD2", cyan="#2AA198", green="#859900", red="#DC322F",
        yellow="#B58900", purple="#6C71C4", pink="#D33682", orange="#CB4B16",
    ),
    "monokai": dict(
        bg="#272822", fg="#F8F8F2",
        accent="#AE81FF", orbit="#66D9EF",
        blue="#66D9EF", cyan="#66D9EF", green="#A6E22E", red="#F92672",
        yellow="#E6DB74", purple="#AE81FF", pink="#F92672", orange="#FD971F",
    ),
    "tokyo-night": dict(
        bg="#1A1B26", fg="#C0CAF5",
        accent="#7AA2F7", orbit="#7DCFFF",
        blue="#7AA2F7", cyan="#7DCFFF", green="#9ECE6A", red="#F7768E",
        yellow="#E0AF68", purple="#BB9AF7", pink="#BB9AF7", orange="#FF9E64",
    ),
    "gruvbox-dark": dict(
        bg="#282828", fg="#EBDBB2",
        accent="#83A598", orbit="#8EC07C",
        blue="#83A598", cyan="#8EC07C", green="#B8BB26", red="#FB4934",
        yellow="#FABD2F", purple="#D3869B", pink="#D3869B", orange="#FE8019",
    ),
    "synthwave": dict(
        bg="#241B2F", fg="#F8F0FF",
        accent="#FF6B6B", orbit="#FFD319",
        blue="#00E5FF", cyan="#00E5FF", green="#3CF26D", red="#FF6B6B",
        yellow="#FFD319", purple="#B14EED", pink="#FF7EDB", orange="#FF9E64",
    ),
    "catppuccin-mocha": dict(
        bg="#1E1E2E", fg="#CDD6F4",
        accent="#89B4FA", orbit="#94E2D5",
        blue="#89B4FA", cyan="#89DCEB", green="#A6E3A1", red="#F38BA8",
        yellow="#F9E2AF", purple="#CBA6F7", pink="#F5C2E7", orange="#FAB387",
    ),
    "rose-pine": dict(
        bg="#191724", fg="#E0DEF4",
        accent="#EBBCBA", orbit="#9CCFD8",
        blue="#31748F", cyan="#9CCFD8", green="#9CCFD8", red="#EB6F92",
        yellow="#F6C177", purple="#C4A7E7", pink="#EBBCBA", orange="#F6C177",
    ),
    "material-palenight": dict(
        bg="#292D3E", fg="#959DCB",
        accent="#82AAFF", orbit="#89DDFF",
        blue="#82AAFF", cyan="#89DDFF", green="#C3E88D", red="#FF5370",
        yellow="#FFCB6B", purple="#C792EA", pink="#F78C6C", orange="#F78C6C",
    ),
    "everforest-dark": dict(
        bg="#2D353B", fg="#D3C6AA",
        accent="#7FBBB3", orbit="#83C092",
        blue="#7FBBB3", cyan="#83C092", green="#A7C080", red="#E67E80",
        yellow="#DBBC7F", purple="#D699B6", pink="#D699B6", orange="#E69875",
    ),
    "one-dark": dict(
        bg="#282C34", fg="#ABB2BF",
        accent="#61AFEF", orbit="#56B6C2",
        blue="#61AFEF", cyan="#56B6C2", green="#98C379", red="#E06C75",
        yellow="#E5C07B", purple="#C678DD", pink="#D19A66", orange="#D19A66",
    ),
    "cyberpunk": dict(
        bg="#0D0221", fg="#E0F8FF",
        accent="#F9008B", orbit="#00F0FF",
        blue="#00F0FF", cyan="#00F0FF", green="#00FF9F", red="#FF2A6D",
        yellow="#FFE600", purple="#B967FF", pink="#F9008B", orange="#FF9E00",
    ),
    "monokai-pro": dict(
        bg="#2D2A2E", fg="#FCFCFA",
        accent="#FFD866", orbit="#FF6188",
        blue="#78DCE8", cyan="#78DCE8", green="#A9DC76", red="#FF6188",
        yellow="#FFD866", purple="#AB9DF2", pink="#FF6188", orange="#FC9867",
    ),
}

def build(name, pal):
    c = {}
    c["brand"] = pal["accent"]
    c["wordmarkHighlight"] = pal["accent"]
    c["wordmarkShadow"] = pal["bg"]
    c["signal"] = pal["accent"]
    c["orbit"] = pal["orbit"]
    c["accent"] = pal["accent"]
    c["userMessageBg"] = pal["bg"]
    c["text"] = pal["fg"]
    c["muted"] = pal["fg"]
    c["dim"] = pal["blue"]
    c["border"] = pal["bg"]
    c["line"] = pal["blue"]
    c["success"] = pal["green"]
    c["warning"] = pal["yellow"]
    c["error"] = pal["red"]

    syn = {}
    syn["blue"] = pal["blue"]
    syn["flamingo"] = pal["orange"]
    syn["green"] = pal["green"]
    syn["mauve"] = pal["purple"]
    syn["overlay2"] = pal["blue"]
    syn["peach"] = pal["orange"]
    syn["pink"] = pal["pink"]
    syn["red"] = pal["red"]
    syn["sapphire"] = pal["cyan"]
    syn["subtext0"] = pal["fg"]
    syn["teal"] = pal["cyan"]
    syn["text"] = pal["fg"]
    syn["yellow"] = pal["yellow"]

    return {
        "name": name,
        "appearance": "dark",
        "colors": c,
        "ansi": DEFAULT_ANSI,
        "syntax": syn,
        "logo": pal["accent"],
    }

for name, pal in THEMES.items():
    theme = build(name, pal)
    path = os.path.join(OUT, f"{name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(theme, f, indent=2)
    print(f"generated: {name}")

print(f"\n{len(THEMES)} themes -> {OUT}")
