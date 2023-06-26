#! /usr/bin/env python

from glob import glob
import markdown2
import os
import re
import shutil

dst_root_dir = "dst"
dst_posts_dir = f"{dst_root_dir}/posts"
dst_css_dir = f"{dst_root_dir}/css"
dst_assets_dir = f"{dst_root_dir}/assets"
src_root_dir = "src"
src_posts_dir = f"{src_root_dir}/posts"
src_css_dir = f"{src_root_dir}/css"
src_assets_dir = f"{src_root_dir}/assets"
post_ignore_delim = "_"

author_name = "John Doe"
author_mail = "johndoe@example.com"
footer_copyright = f"&copy; 2023 {author_name}"


def dedent(text: str) -> str:
    """Dedents the indentation common to all lines in the text"""
    common_indent = re.match(r"^(\s*)[^s]", text)[1]
    unindent = f"^{common_indent}"
    return re.sub(unindent, "", text, flags=re.MULTILINE)


def initialize_directories():
    """Removes old build artefacts, and generates the build directories

    The /dst directory is the root directory of the blog
    The /dst/posts directory contains all the blog post files
    The /dst/assets directory stores images, videos etc of posts
    The /dst/css directory contains the style sheets of the blog
    """
    shutil.rmtree(dst_root_dir, ignore_errors=True)

    # Create output directories
    for d in (dst_root_dir, dst_posts_dir, dst_css_dir, dst_assets_dir):
        os.makedirs(d, exist_ok=True)

    for f in glob(f"{src_css_dir}/*.css"):
        shutil.copy(f, dst_css_dir)
    shutil.copytree(src_assets_dir, dst_assets_dir, dirs_exist_ok=True)

    print("Build directories initialized.")


def parse_header(src_post) -> dict[str, str]:
    """Parses the header and returns a dictionary of fields from it.
    """

    print(f"Parsing post {src_post} ...")

    with open(src_post, encoding="utf-8") as f:
        lines = f.readlines()

    patterns = (
        # Line 1: Check for --- start-marker
        (r"^---\s*$",
         "Starting markers missing or incorrect"),
        # Line 2: Check for title-field
        (r"^title:\s*(?P<title>.*)\s*$",
         "Title field missing or incorrect"),
        # Line 3: Check for description-field
        (r"^description:\s*(?P<description>.*)\s*$",
         "Description field missing or incorrect"),
        # Line 4: Check for date-field with valid date in YYYY-MM-DD format
        (r"^date:\s*(?P<date>[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[1-2][0-9]|3[0-1]))\s*$",
         "Date field missing, incorrect or in wrong format."),
        # Line 5: Check for tags-field
        (r"^tags:\s*(?P<tags>.*)\s*$",
         "Tags field missing or incorrect"),
        # Line 6: Check for --- end-marker
        (r"^---\s*$",
         "Ending marker missing or incorrect")
    )
    results: dict[str, str] = {}
    for line, pat_msg in zip(lines, patterns):
        pattern, msg = pat_msg
        match = re.match(pattern, line)
        if match:
            results |= match.groupdict()
        else:
            print(f"{src_post}: Invalid header \"{line}\".\n{msg}")
            return {}
    return results


def build_page(src_md: str, dst_html: str, root: str):
    """Converts the markdown post or page into html format.

    During this process, the header is prepended and the footer appended to the post.
    Arguments:

      src_md: The source path to the markdown post/page file
      dst_html: The destination file where the converted html file will be saved.
    """

    md = markdown2.Markdown(extras=["metadata"])
    with open(src_md, encoding='utf-8') as f:
        html = md.convert(f.read())

    with open(dst_html, "w", encoding='utf-8') as f:
        f.write(dedent(f"""\
            <html>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link rel="stylesheet" href="{root}/css/normalize.css" type="text/css" media="all">
            <link rel="stylesheet" href="{root}/css/style.css" type="text/css" media="all">
            <nav>
            <a href="{root}/index.html">home</a>
            <a href="{root}/articles.html">articles</a>
            <a href="mailto:{author_mail}">mail</a>
            <a href="{root}/about.html">about</a>
            </nav>
            <hr>"""))
        f.write(html)
        f.write(dedent(f"""\
            </main>
            <footer>
            <hr>
            <p>
            {footer_copyright}
            <br/>
            </p>
            </footer>
            </body>
            </html>"""))


def process_files(src_posts_dir) -> list[dict[str, str]]:
    """
    Iterate through all source post files, and extract values stored in their headers
    such as date, title, but also stores source path and destination path.
    Return the list of dictionaries containing the data of the posts.
    """

    # Find all .md posts in the post directory and extract info from the headers
    posts = []
    for src_post_path in glob(f"{src_posts_dir}/*.md"):
        post = parse_header(src_post_path)
        if post:
            post["basename"] = os.path.basename(src_post_path)
            root_name, _ext = os.path.splitext(post["basename"])
            dst_post_path = f"{dst_posts_dir}/{root_name}.html"
            post["src"] = src_post_path
            post["dst"] = dst_post_path
            posts.append(post)
    return posts


def sort_posts(posts: list[dict[str, str]]) -> list[dict[str, str]]:
    """Sorts posts in place in reverse chronological order, based on the extracted date"""
    def key(post): return post["date"]
    posts.sort(key=key)
    return posts


if __name__ == "__main__":
    initialize_directories()
    build_page(f"{src_root_dir}/about.md", f"{dst_root_dir}/about.html", ".")
    build_page(f"{src_root_dir}/index.md", f"{dst_root_dir}/index.html", ".")
    build_page(f"{src_root_dir}/articles.md",
               f"{dst_root_dir}/articles.html", ".")
    posts = process_files(src_posts_dir)
    posts = sort_posts(posts)

    posts_processed = 0
    posts_skipped = 0

    article_list = '<ul class="articles">\n'

    for post in posts:
        dst_link = post["dst"][len("dst/"):]
        print(f'Processing post: {post["src"]}')
        print(f'    title:  {post["title"]}')
        print(f'    date:   {post["date"]}')
        print(f'    output: {post["dst"]}')

        if post["basename"].startswith(post_ignore_delim):
            posts_skipped += 1
        else:
            article_list += f'<li><b style="color: #14263b;">{post["date"]}</b> <a href="{dst_link}">{post["title"]}</a></li>\n'
            build_page(post["src"], post["dst"], "..")
            posts_processed += 1

    article_list += '</ul>'

    print("Generating article listing ...")

    # Replace article tags in the article.html file with the generated article list
    with open(f"{dst_root_dir}/articles.html", encoding="utf-8") as f:
        articles_html = f.read()

    articles_html = articles_html.replace(
        "<article>", f"<article>\n{article_list}")

    with open(f"{dst_root_dir}/articles.html", "w", encoding="utf-8") as f:
        f.write(articles_html)

    print(f"Finished! (built: {posts_processed}, skipped: {posts_skipped})")
