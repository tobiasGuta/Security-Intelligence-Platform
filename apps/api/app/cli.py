import asyncio
import click
from sqlalchemy import select
from app.db.engine import async_session_factory
from app.models.user import User
from app.core.security import hash_password

async def create_user_async(username, email, password, is_superuser):
    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.username == username))
        if result.scalar_one_or_none():
            click.echo(f"User {username} already exists.")
            return

        user = User(
            username=username,
            email=email,
            hashed_password=hash_password(password),
            is_superuser=is_superuser,
            is_active=True
        )
        session.add(user)
        await session.commit()
        click.echo(f"User {username} created successfully.")

@click.group()
def cli():
    pass

@cli.command()
@click.option('--username', prompt=True)
@click.option('--email', prompt=True)
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True)
def create_admin(username, email, password):
    asyncio.run(create_user_async(username, email, password, True))

@cli.command()
def seed_dev():
    click.secho("!!! WARNING: DEV ONLY !!!", fg="red", bold=True)
    asyncio.run(create_user_async("devadmin", "dev@example.com", "devpass123", True))
    click.echo("Credentials: devadmin / devpass123")

if __name__ == '__main__':
    cli()
