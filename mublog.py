#! /usr/bin/env python

from glob import glob
from string import Template
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

    title = f"<title>{metadata['title']}</title>\n" if "title" in md.metadata else ""

    substitutions = {
        "author_mail": author_mail,
        "contents": html,
        "footer_copyright": footer_copyright,
        "root": root,
        "title": title,
    }
    substitute(substitutions, f"{src_root_dir}/post.html", dst_html)

    return metadata


def convert_md_files(path: str, root: str) -> list[dict[str, str]]:
    """
    Iterate through all .md files in a directory, write out the html converted result,
    and return a list of their metadata dictionaries.
    """

    # Find all .md files in the directory, convert them, and collect metadata
    metadata_list = []
    for src_post_path in glob(f"{path}/*.md"):
        basename = os.path.basename(src_post_path)
        if not basename.startswith(post_ignore_delim):
            root_name, _ext = os.path.splitext(basename)
            dst_post_path = f"{dst_posts_dir}/{root_name}.html"

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
    convert_md_file(f"{src_root_dir}/about.md",
                    f"{dst_root_dir}/about.html", ".")
    convert_md_file(f"{src_root_dir}/index.md",
                    f"{dst_root_dir}/index.html", ".")
    convert_md_file(f"{src_root_dir}/articles.md",
                    f"{dst_root_dir}/articles.html", ".")

    metadata_list = convert_md_files(src_posts_dir, "..")
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
            dst_link = metadata["dst"][len("dst/"):]
            article_list += f'<li><b style="color: #14263b;">{date}</b> <a href="{dst_link}">{title}</a></li>\n'
            posts_processed += 1

    article_list += '</ul>'

    print("Generating article listing ...")

    substitute({"articles": article_list}, f"{dst_root_dir}/articles.html")

    print(f"Finished! (built: {posts_processed}, skipped: {posts_skipped})")
