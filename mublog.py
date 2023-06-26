#! /usr/bin/env python

from configparser import ConfigParser, ExtendedInterpolation
from glob import glob
from string import Template
import markdown2
import os
import re
import shutil

config = ConfigParser(interpolation=ExtendedInterpolation())
config.read("config.ini")


def path(key: str, filename: str = None) -> str:
    path = config['Paths'][key]
    return f"{path}/{filename}" if filename else f"{path}/"


def readfile(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def writefile(path: str, contents: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(contents)


def substitute(mapping: dict[str, str], in_path: str, out_path: str = None):
    if not out_path:
        out_path = in_path

    template_text = readfile(in_path)
    template = Template(template_text)
    output = template.substitute(mapping)
    writefile(out_path, output)


def initialize_directories():
    """Removes old build artefacts, and generates the build directories"""
    if os.path.exists(path("dst_root")):
        shutil.rmtree(path("dst_root"))

    for d in (path("dst_root"), path("dst_posts"), path("dst_css")):
        os.makedirs(d, exist_ok=True)

    for css in glob(path("src_css", "*.css")):
        shutil.copy(css, path("dst_css"))

    shutil.copytree(path("src_assets"), path("dst_assets"))

    print("Build directories initialized.")


def convert_md_file(src_md: str, dst_html: str, root: str) -> dict[str, str]:
    """Converts the markdown post or page into html format.

    During this process, the header is prepended and the footer appended to the post.
    Arguments:

      src_md: The source path to the markdown post/page file
      dst_html: The destination file where the converted html file will be saved.

    Returns:
      metadata from the markdown file
    """

    md = markdown2.Markdown(extras=["metadata"])
    html = md.convert(readfile(src_md))
    metadata = md.metadata
    metadata["src"] = src_md
    metadata["dst"] = dst_html
    metadata["dst_link"] = dst_html.removeprefix(path("dst_root"))

    title = f"<title>{metadata['title']}</title>\n" if "title" in md.metadata else ""

    substitutions = {
        "author_mail": config["Author"]["mail"],
        "contents": html,
        "footer": config["Layout"]["footer"],
        "root": root,
        "title": title,
    }
    substitute(substitutions, path("src_root", "post.html"), dst_html)

    return metadata


def convert_md_files(_path: str, root: str) -> list[dict[str, str]]:
    """
    Iterate through all .md files in a directory, write out the html converted result,
    and return a list of their metadata dictionaries.
    """

    draft_prefix = config["Paths"]["draft_prefix"]
    metadata_list = []
    for src_post_path in glob(f"{_path}/*.md"):
        basename = os.path.basename(src_post_path)
        if not basename.startswith(draft_prefix):
            root_name, _ext = os.path.splitext(basename)
            dst_post_path = path("dst_posts", f"{root_name}.html")

            print(f'Processing post: {src_post_path}')
            metadata = convert_md_file(src_post_path, dst_post_path, root)
            metadata["basename"] = basename

            print(f'    title:  {metadata["title"]}')
            print(f'    date:   {metadata["date"]}')
            print(f'    output: {metadata["dst"]}')
            metadata_list.append(metadata)
        else:
            metadata_list.append({"skipped": src_post_path})

    return metadata_list


def sort_metadata(metadata: list[dict[str, str]]):
    """Sorts posts in place in reverse chronological order, based on date"""
    def key(metadata): return metadata["date"]
    metadata.sort(key=key)


if __name__ == "__main__":
    initialize_directories()
    convert_md_file(path("src_root", "about.md"),
                    path("dst_root", "about.html"), ".")
    convert_md_file(path("src_root", "index.md"),
                    path("dst_root", "index.html"), ".")
    convert_md_file(path("src_root", "articles.md"),
                    path("dst_root", "articles.html"), ".")

    metadata_list = convert_md_files(path("src_posts"), "..")
    sort_metadata(metadata_list)

    posts_processed = 0
    posts_skipped = 0

    article_list = '<ul class="articles">\n'

    for metadata in metadata_list:
        if "skipped" in metadata:
            posts_skipped += 1
        else:
            date = metadata["date"]
            title = metadata["title"]
            dst_link = metadata["dst_link"]
            article_list += f'<li><b style="color: #14263b;">{date}</b> <a href="{dst_link}">{title}</a></li>\n'
            posts_processed += 1

    article_list += '</ul>'

    print("Generating article listing ...")

    substitute({"articles": article_list}, path("dst_root", "articles.html"))

    print(f"Finished! (built: {posts_processed}, skipped: {posts_skipped})")
