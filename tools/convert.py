"""Build the static site from the Claude Design canvas.

Usage: python -I tools/convert.py <download>/project <site root>

<download> holds the canvas files: project/ with every <Name>.dc.html board, and next to it
each asset the boards use, saved as <id>.<ext> (the id from /_blob/<id> or B('<id>')).
It deletes every *.html page in the site root first, then writes each board as a page (names
in PAGES; Blog-* boards become blog-*.html). Assets go to assets/img and assets/files, and the
dark theme to assets/css/theme.css. tools/site_edits.py runs at the end. If a run stops with
an error, pages are missing until a run succeeds.
"""
import re, sys, json, shutil, pathlib

src = pathlib.Path(sys.argv[1])      # .../project
out = pathlib.Path(sys.argv[2])      # site root
blobs = src.parent                   # downloaded assets: <id>.<ext>

PAGES = {
    'Landing': 'index.html', 'Vision': 'vision.html', 'WhitePaper': 'white-paper.html',
    'Pricing': 'pricing.html', 'Careers': 'careers.html', 'SignIn': 'sign-in.html',
    'Blog': 'blog.html', 'Newsroom': 'newsroom.html',
    'Main': 'today.html', 'Session': 'session.html', 'Map': 'map.html', 'Notes': 'notes.html',
    'Webs': 'connects.html', 'Profile': 'profile.html', 'Copilot': 'copilot.html',
    'Passport': 'passport.html', 'Engine': 'loop.html',
    'Assessments': 'assessments.html', 'Onboarding': 'onboarding.html', 'Learner': 'learner.html',
    'Messages': 'messages.html', 'Clubs': 'clubs.html', 'Showcase': 'showcase.html',
    'Compare': 'compare.html', 'Approvals': 'approvals.html',
    'HowItWorks': 'how-it-works.html',
    'Guide': 'guide.html', 'School': 'school.html', 'Ops': 'ops.html', 'About': 'about.html', 'Admin': 'admin.html', 'SuperAdmin': 'super-admin.html', 'BlogAdmin': 'blog-admin.html', 'Studio': 'studio.html', 'Contribute': 'contribute.html',
    'Calendar': 'calendar.html', 'DesignSystem': 'design-system.html', 'Join': 'join.html', 'Enrol': 'enrol.html',
    'MyStudio': 'my-studio.html', 'Notebook': 'notebook.html',
    'Checkout': 'checkout.html', 'GuideVerify': 'guide-checks.html', 'Help': 'help.html', 'LowBandwidth': 'any-phone.html',
    'MobileLearner': 'mobile-learner.html', 'MobileParent': 'mobile-parent.html', 'NotifySettings': 'notifications.html',
    'PageStates': 'page-states.html', 'Status': 'status.html',
    'ComingSoon': 'coming-soon.html',  # tools/site_edits.py moves it to index.html
    'LiveRoom': 'live-room.html', 'ParentApprovals': 'parent-approvals.html',
    'ParentFamily': 'parent-family.html', 'ParentMoney': 'parent-money.html',
    'Privacy': 'privacy.html', 'Strengths': 'strengths.html', 'Terms': 'terms.html',
}
for f in sorted(src.glob('Blog-*.dc.html')):
    stem = f.name[:-len('.dc.html')]
    PAGES[stem] = stem.lower() + '.html'

DARK = {'Engine'}
NO_THEME = {'ComingSoon'}
NAMED_IMAGES = {
    '130b3312f250a525b36f83ac7dbcd1ad': 'logo.png',
    '95e7c60fb0d5dd727c608b67609dd5fc': 'logo-white.png',
    '8d28dd56ebdb418f1a860c72bfe54019': 'mark.png',
    '722f162bd5a6fbe9b8a40b8154a9cbf6': 'mark-white.png',
    'd2b338401f21c3c4b3f1e0958c25effb': 'logo-dark.png',
}
THEME_CSS = '923073ef2686e5b047e222dac6352bdb'
IMAGE_EXT = {'.png', '.jpg', '.jpeg', '.webp', '.svg', '.gif'}
FONTS = ('https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400..800;1,400..800'
         '&amp;family=Inter:wght@400;500;600;700&amp;display=swap')
# Helmet rules already provided by assets/css/site.css
BASE_CSS = {
    'body{margin:0}', 'body{margin:0;background:#F4F4EF}', 'a{color:#1D4ED8}a:hover{color:#1E40AF}',
    "button,input,textarea,select,label,nav{font-family:Inter,system-ui,-apple-system,'Segoe UI',sans-serif}",
    ':focus-visible{outline:2px solid #1D4ED8;outline-offset:2px}', 'html{scroll-behavior:smooth}',
    'body{margin:0;background:#111315}', 'a{color:#7DB4FF}a:hover{color:#AFD0FF}',
    ':focus-visible{outline:2px solid #7DB4FF;outline-offset:2px}',
}

# Images go to assets/img, documents and media (PDF, MP4, CSV, JSON) to assets/files
asset_dirs = {'img': out / 'assets' / 'img', 'files': out / 'assets' / 'files'}
for d in asset_dirs.values():
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
image_names = {}
for f in blobs.iterdir():
    if f.is_file() and re.fullmatch(r'[0-9a-f]{32}\.\w+', f.name) and f.stem != THEME_CSS:
        kind = 'img' if f.suffix.lower() in IMAGE_EXT else 'files'
        image_names[f.stem] = kind + '/' + NAMED_IMAGES.get(f.stem, f.name)


def rewrite(code, used):
    def img(m):
        used.add(m.group(1))
        return 'assets/' + image_names[m.group(1)]
    code = re.sub(r'/_blob/([0-9a-f]{32})', img, code)
    for s, t in PAGES.items():
        code = re.sub(rf"(['\"`]){re.escape(s)}\.dc\.html", rf'\g<1>{t}', code)
        # Bare mentions too, e.g. in code comments: "(Enrol.dc.html)"
        code = re.sub(rf"(?<![\w-]){re.escape(s)}\.dc\.html", t, code)
    return code


def parse(stem, used):
    html = (src / f'{stem}.dc.html').read_text(encoding='utf-8')
    title = re.search(r'<title>(.*?)</title>', html, re.S).group(1)
    body = re.search(r'<x-dc>(.*?)</x-dc>', html, re.S).group(1)
    helmet = re.search(r'<helmet>(.*?)</helmet>', body, re.S).group(1)
    body = re.sub(r'<helmet>.*?</helmet>\s*', '', body, flags=re.S)
    tag = re.search(r'<script type="text/x-dc"[^>]*>', html).group(0)
    script = re.search(r'<script type="text/x-dc"[^>]*>(.*?)</script>', html, re.S).group(1)

    assert helmet.count('<link') == 1, stem
    fonts = re.search(r'<link rel="stylesheet" href="([^"]*)">', helmet).group(1)
    # Every page loads the base families; some add more (e.g. Caveat)
    assert fonts.startswith('https://fonts.googleapis.com/css2?family=EB+Garamond:') and 'family=Inter:' in fonts and fonts.endswith('&amp;display=swap'), stem
    css = re.search(r'<style>(.*?)</style>', helmet, re.S).group(1)
    css = '\n'.join(l for l in css.strip().splitlines() if l.strip() and l.strip() not in BASE_CSS)

    props = json.loads(re.search(r"data-props='([^']*)'", tag).group(1))
    defaults = {k: v['default'] for k, v in props.items() if k != '$preview' and 'default' in v}

    body = re.sub(r'\s+hint-[a-z-]+="[^"]*"', '', body)
    body = re.sub(r'<sc-for list="([^"]*)" as="([^"]*)">', r'<template data-for="\1" data-as="\2">', body)
    body = re.sub(r'<sc-if value="([^"]*)">', r'<template data-if="\1">', body)
    body = re.sub(r'</sc-(for|if)>', '</template>', body)
    body = rewrite(body, used)

    # Scripts that build asset or page URLs at runtime
    script = script.replace("const B = (id) => '/_blob/' + id;", "const B = (id) => 'assets/img/' + id + '.svg';")
    script = script.replace("'Blog-' + r[0] + '.dc.html'", "'blog-' + r[0] + '.html'")
    # Page URLs built at runtime from a board name, e.g. r.n + '.dc.html#state=empty' (PageStates)
    if re.search(r"[\w.\]\)]+ \+ '\.dc\.html", script):
        pmap = dict(PAGES); pmap['ComingSoon'] = './'  # the Coming soon board is the site root (tools/site_edits.py)
        script = re.sub(r"([\w.]+) \+ '\.dc\.html", r"__dcPage(\1) + '", script)
        script = 'const __dcPage = (n) => (' + json.dumps(pmap) + "[n] || String(n).toLowerCase() + '.html');\n" + script
    for i in re.findall(r"B\('([0-9a-f]{32})'\)", script):
        assert image_names[i] == 'img/' + i + '.svg', i
        used.add(i)
    script = rewrite(script, used)

    # Every board loads the shared dark theme, except ComingSoon, which has its own styles
    assert f'/_blob/{THEME_CSS}' in html.split('<x-dc>')[0] or stem in NO_THEME, stem
    for code in (body, script):
        assert '_blob' not in code and '.dc.html' not in code and '<sc-' not in code, stem
    return dict(title=title, fonts=fonts, body=body.strip(), script=script.strip(), css=css, defaults=defaults)


used = set()
for f in out.glob('*.html'):
    f.unlink()

for stem, target in PAGES.items():
    page = parse(stem, used)
    parts = [(stem, page)]
    for name in dict.fromkeys(re.findall(r'<dc-import name="(\w+)"', page['body'])):
        parts.append((name, parse(name, used)))

    css = '\n'.join(p['css'] for _, p in parts if p['css'])
    style = f'<style>\n{css}\n</style>\n' if css else ''
    templates = '\n'.join(f'<template id="dc-{n}">\n{p["body"]}\n</template>' for n, p in parts)
    scripts = '\n\n'.join(
        f'DC.component({json.dumps(n)}, function () {{\n{p["script"]}\nreturn Component;\n}}'
        + (f', {json.dumps(p["defaults"], ensure_ascii=False)}' if p['defaults'] else '') + ');'
        for n, p in parts)
    fonts = max((p['fonts'] for _, p in parts), key=len)
    body_attr = ' class="theme-dark"' if stem in DARK else ''
    html = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{page["title"]}</title>
<link rel="icon" type="image/png" href="assets/img/mark.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{fonts}">
<link rel="stylesheet" href="assets/css/site.css">
<link rel="stylesheet" href="assets/css/theme.css">
{style}<script src="assets/js/dc.js"></script>
</head>
<body{body_attr}>
<div id="app"></div>
{templates}
<script>
{scripts}

DC.mount({json.dumps(stem)});
</script>
</body>
</html>
'''
    (out / target).write_text(html, encoding='utf-8', newline='\n')
    print(stem, '->', target)

# Site edits kept in the repo (changes the canvas doesn't have), re-applied on every build
import subprocess
subprocess.run([sys.executable, '-I', str(out / 'tools' / 'site_edits.py'), str(out)], check=True)

# Dark theme: selectors match the page's image paths; url() is relative to assets/css
theme = (blobs / f'{THEME_CSS}.css').read_text(encoding='utf-8')
theme = re.sub(r'url\("/_blob/([0-9a-f]{32})"\)', lambda m: (used.add(m.group(1)), f'url("../{image_names[m.group(1)]}")')[1], theme)
theme = rewrite(theme, used)
assert '_blob' not in theme
(out / 'assets' / 'css' / 'theme.css').write_text(theme, encoding='utf-8', newline=chr(10))

for i in used:
    shutil.copyfile(next(f for f in blobs.glob(i + '.*') if f.stem == i), out / 'assets' / image_names[i])
print(len(used), 'assets')
