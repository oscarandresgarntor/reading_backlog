"""CLI commands for the reading backlog."""

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from ..models import Article, ArticleCreate, ArticleUpdate, Priority, Status
from ..services import scrape_article_sync, storage, is_ollama_running
from ..services.scraper import extract_pdf_metadata, merge_tags

app = typer.Typer(
    name="reading",
    help="Manage your reading backlog from the terminal.",
    no_args_is_help=True,
)
console = Console()


def format_priority(priority: Priority) -> str:
    """Format priority with color."""
    colors = {"high": "red", "medium": "yellow", "low": "green"}
    return f"[{colors[priority.value]}]{priority.value}[/{colors[priority.value]}]"


def format_status(status: Status) -> str:
    """Format status with styling."""
    if status == Status.READ:
        return "[dim]read[/dim]"
    return "[bold]unread[/bold]"


def truncate(text: str, length: int = 50) -> str:
    """Truncate text to specified length."""
    if len(text) <= length:
        return text
    return text[:length - 3] + "..."


@app.command()
def list(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter: unread, read"),
    priority: Optional[str] = typer.Option(None, "--priority", "-p", help="Filter: low, medium, high"),
    tag: Optional[str] = typer.Option(None, "--tag", "-t", help="Filter by tag"),
    source: Optional[str] = typer.Option(None, "--source", help="Filter by source domain"),
):
    """List all articles in the backlog."""
    # Convert string filters to enums
    status_filter = Status(status) if status else None
    priority_filter = Priority(priority) if priority else None

    articles = storage.get_all(
        status=status_filter,
        priority=priority_filter,
        tag=tag,
        source=source,
    )

    if not articles:
        console.print("[dim]No articles found.[/dim]")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("ID", style="dim", width=8)
    table.add_column("Title", width=40)
    table.add_column("Source", width=15)
    table.add_column("Priority", width=8)
    table.add_column("Status", width=8)
    table.add_column("Tags", width=15)

    for article in articles:
        table.add_row(
            article.id[:8],
            truncate(article.title, 40),
            truncate(article.source, 15),
            format_priority(article.priority),
            format_status(article.status),
            ", ".join(article.tags[:3]) if article.tags else "-",
        )

    console.print(table)
    console.print(f"\n[dim]Total: {len(articles)} articles[/dim]")


@app.command()
def add(
    url: str = typer.Argument(..., help="URL of the article to add"),
    tags: Optional[str] = typer.Option(None, "--tags", "-t", help="Comma-separated tags"),
    priority: str = typer.Option("medium", "--priority", "-p", help="Priority: low, medium, high"),
):
    """Add a new article to the backlog."""
    with console.status("Fetching article metadata..."):
        try:
            article_data = ArticleCreate(
                url=url,
                tags=tags.split(",") if tags else [],
                priority=Priority(priority),
            )
            article = scrape_article_sync(article_data)
            storage.add(article)

            console.print(f"\n[green]Added:[/green] {article.title}")
            console.print(f"[dim]Source: {article.source} | ID: {article.id[:8]}[/dim]")
            if article.summary:
                console.print(f"[dim]{article.summary}[/dim]")

        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)


@app.command("add-local")
def add_local(
    file_path: str = typer.Argument(..., help="Path to local PDF file"),
    tags: Optional[str] = typer.Option(None, "--tags", "-t", help="Comma-separated tags"),
    priority: str = typer.Option("medium", "--priority", "-p", help="Priority: low, medium, high"),
):
    """Add a local PDF file to the backlog."""
    from pathlib import Path

    path = Path(file_path).expanduser().resolve()

    if not path.exists():
        console.print(f"[red]Error:[/red] File not found: {path}")
        raise typer.Exit(1)

    if not path.suffix.lower() == ".pdf":
        console.print(f"[red]Error:[/red] Only PDF files are supported")
        raise typer.Exit(1)

    status_msg = "Analyzing PDF with LLM..." if is_ollama_running() else "Extracting PDF metadata..."
    with console.status(status_msg):
        try:
            pdf_bytes = path.read_bytes()
            pdf_meta = extract_pdf_metadata(pdf_bytes, str(path), use_llm=True)

            # Merge user tags with LLM-suggested tags
            user_tags = [t.strip() for t in tags.split(",")] if tags else []
            all_tags = merge_tags(user_tags, pdf_meta.get("suggested_tags", []))

            article = Article(
                url=f"file://{path}",
                title=pdf_meta["title"],
                summary=pdf_meta["summary"],
                source=path.name,
                date_published=pdf_meta["date_published"],
                tags=all_tags,
                priority=Priority(priority),
            )
            storage.add(article)

            llm_note = " [cyan](via LLM)[/cyan]" if pdf_meta.get("used_llm") else ""
            console.print(f"\n[green]Added:{llm_note}[/green] {article.title}")
            console.print(f"[dim]Source: {article.source} | ID: {article.id[:8]}[/dim]")
            if article.summary:
                console.print(f"[dim]{article.summary}[/dim]")
            if all_tags:
                console.print(f"[dim]Tags: {', '.join(all_tags)}[/dim]")

        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)


@app.command()
def read(
    article_id: str = typer.Argument(..., help="Article ID (first 8 chars or full)"),
):
    """Mark an article as read."""
    # Find article by partial ID
    articles = storage.get_all()
    matches = [a for a in articles if a.id.startswith(article_id)]

    if not matches:
        console.print(f"[red]No article found with ID starting with '{article_id}'[/red]")
        raise typer.Exit(1)
    if len(matches) > 1:
        console.print(f"[yellow]Multiple matches. Please be more specific:[/yellow]")
        for a in matches:
            console.print(f"  {a.id[:8]} - {truncate(a.title, 50)}")
        raise typer.Exit(1)

    article = matches[0]
    storage.update(article.id, ArticleUpdate(status=Status.READ))
    console.print(f"[green]Marked as read:[/green] {article.title}")


@app.command()
def unread(
    article_id: str = typer.Argument(..., help="Article ID (first 8 chars or full)"),
):
    """Mark an article as unread."""
    articles = storage.get_all()
    matches = [a for a in articles if a.id.startswith(article_id)]

    if not matches:
        console.print(f"[red]No article found with ID starting with '{article_id}'[/red]")
        raise typer.Exit(1)
    if len(matches) > 1:
        console.print(f"[yellow]Multiple matches. Please be more specific:[/yellow]")
        for a in matches:
            console.print(f"  {a.id[:8]} - {truncate(a.title, 50)}")
        raise typer.Exit(1)

    article = matches[0]
    storage.update(article.id, ArticleUpdate(status=Status.UNREAD))
    console.print(f"[green]Marked as unread:[/green] {article.title}")


@app.command()
def delete(
    article_id: str = typer.Argument(..., help="Article ID (first 8 chars or full)"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Delete an article from the backlog."""
    articles = storage.get_all()
    matches = [a for a in articles if a.id.startswith(article_id)]

    if not matches:
        console.print(f"[red]No article found with ID starting with '{article_id}'[/red]")
        raise typer.Exit(1)
    if len(matches) > 1:
        console.print(f"[yellow]Multiple matches. Please be more specific:[/yellow]")
        for a in matches:
            console.print(f"  {a.id[:8]} - {truncate(a.title, 50)}")
        raise typer.Exit(1)

    article = matches[0]

    if not force:
        confirm = typer.confirm(f"Delete '{article.title}'?")
        if not confirm:
            raise typer.Abort()

    storage.delete(article.id)
    console.print(f"[red]Deleted:[/red] {article.title}")


@app.command()
def show(
    article_id: str = typer.Argument(..., help="Article ID (first 8 chars or full)"),
):
    """Show full details of an article."""
    articles = storage.get_all()
    matches = [a for a in articles if a.id.startswith(article_id)]

    if not matches:
        console.print(f"[red]No article found with ID starting with '{article_id}'[/red]")
        raise typer.Exit(1)
    if len(matches) > 1:
        console.print(f"[yellow]Multiple matches. Please be more specific:[/yellow]")
        for a in matches:
            console.print(f"  {a.id[:8]} - {truncate(a.title, 50)}")
        raise typer.Exit(1)

    article = matches[0]

    console.print(f"\n[bold]{article.title}[/bold]")
    console.print(f"[dim]{'─' * 60}[/dim]")
    console.print(f"[cyan]URL:[/cyan] {article.url}")
    console.print(f"[cyan]Source:[/cyan] {article.source}")
    console.print(f"[cyan]Status:[/cyan] {format_status(article.status)}")
    console.print(f"[cyan]Priority:[/cyan] {format_priority(article.priority)}")
    console.print(f"[cyan]Added:[/cyan] {article.date_added.strftime('%Y-%m-%d %H:%M')}")
    if article.date_published:
        console.print(f"[cyan]Published:[/cyan] {article.date_published}")
    if article.tags:
        console.print(f"[cyan]Tags:[/cyan] {', '.join(article.tags)}")
    if article.summary:
        console.print(f"\n[cyan]Summary:[/cyan]\n{article.summary}")
    console.print(f"\n[dim]ID: {article.id}[/dim]")


@app.command()
def export(
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
):
    """Export backlog to Markdown file."""
    from pathlib import Path

    output_path = Path(output) if output else None
    result = storage.export_markdown(output_path)
    console.print(f"[green]Exported to:[/green] {result}")


@app.command()
def tag(
    article_id: str = typer.Argument(..., help="Article ID (first 8 chars or full)"),
    tags: str = typer.Argument(..., help="Comma-separated tags to set"),
):
    """Update tags for an article."""
    articles = storage.get_all()
    matches = [a for a in articles if a.id.startswith(article_id)]

    if not matches:
        console.print(f"[red]No article found with ID starting with '{article_id}'[/red]")
        raise typer.Exit(1)
    if len(matches) > 1:
        console.print(f"[yellow]Multiple matches. Please be more specific:[/yellow]")
        for a in matches:
            console.print(f"  {a.id[:8]} - {truncate(a.title, 50)}")
        raise typer.Exit(1)

    article = matches[0]
    new_tags = [t.strip() for t in tags.split(",") if t.strip()]
    storage.update(article.id, ArticleUpdate(tags=new_tags))
    console.print(f"[green]Updated tags:[/green] {', '.join(new_tags)}")


@app.command()
def priority(
    article_id: str = typer.Argument(..., help="Article ID (first 8 chars or full)"),
    level: str = typer.Argument(..., help="Priority: low, medium, high"),
):
    """Update priority for an article."""
    articles = storage.get_all()
    matches = [a for a in articles if a.id.startswith(article_id)]

    if not matches:
        console.print(f"[red]No article found with ID starting with '{article_id}'[/red]")
        raise typer.Exit(1)
    if len(matches) > 1:
        console.print(f"[yellow]Multiple matches. Please be more specific:[/yellow]")
        for a in matches:
            console.print(f"  {a.id[:8]} - {truncate(a.title, 50)}")
        raise typer.Exit(1)

    article = matches[0]
    try:
        new_priority = Priority(level)
        storage.update(article.id, ArticleUpdate(priority=new_priority))
        console.print(f"[green]Updated priority:[/green] {format_priority(new_priority)}")
    except ValueError:
        console.print(f"[red]Invalid priority. Use: low, medium, high[/red]")
        raise typer.Exit(1)


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
