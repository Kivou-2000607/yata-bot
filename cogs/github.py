# import standard modules
import asyncio
import requests
import time

# import discord modules
from discord.ext import commands
from discord import Embed

# import bot functions and classes
import includes.checks as checks
import includes.formating as fmt
from includes.github import Repository


class Github(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def issues(self, ctx):
        """list issues"""

        # check role and channel
        ALLOWED_CHANNELS = ["bug-report", "issues", "github"]
        # ALLOWED_ROLES = ["Verified"]
        # if await checks.roles(ctx, ALLOWED_ROLES) and await checks.channels(ctx, ALLOWED_CHANNELS):
        if await checks.channels(ctx, ALLOWED_CHANNELS):
            pass
        else:
            return

        # list of embeds
        embeds = []

        # get repo
        repo = Repository()

        # repo.create_issue("Test", "couocu", "bug")

        # loop over issues
        for i in repo.get_issues():
            title = f'Issue #{i.number:03d}: {i.title}'
            msg = [f'{i.url}']
            # if i.body:
            #     msg.append(f'\n{i.user.login}:\n---\n{i.body}\n---\n')

            embed = Embed(title=title, description="\n".join(msg), color=550000)

            assignees = [ass.login for ass in i.assignees if ass is not None]
            if len(assignees):
                embed.add_field(name='Assignees', value=f'{", ".join(assignees)}')
            else:
                embed.add_field(name='Assignees', value='None')

            if i.milestone is not None:
                embed.add_field(name='For version', value=f'{i.milestone.title}')
            else:
                embed.add_field(name='For version', value=f'Not defined')

            if i.assignee is not None:
                embed.set_thumbnail(url=i.user.avatar_url)

            embed.set_footer(text=f'Labels: {", ".join([lab.name for lab in i.labels])}\t')

            # add embed
            embeds.append(embed)
            await ctx.send(embed=embed)

    @commands.command()
    async def bug(self, ctx, *arg):
        """report a but"""

        # check role and channel
        ALLOWED_CHANNELS = ["bug-report", "suggestions", "issues", "github"]
        ALLOWED_ROLES = ["Verified"]
        if await checks.roles(ctx, ALLOWED_ROLES) and await checks.channels(ctx, ALLOWED_CHANNELS):
            pass
        else:
            return

        try:
            # get repo
            repo = Repository()

            if len(arg) == 0:
                await ctx.send(f'You need to give a title to your bug: `!bug this is not working`')
            else:
                repo.create_issue(" ".join(arg), f'Created by {ctx.author.display_name}', "bug")
                await ctx.send(f'Your bug has been reported. Thank you.')

        except BaseException as e:
            await ctx.send(f'Failed to create the issue: {e}')

    @commands.command()
    async def request(self, ctx, *arg):
        """make a request"""

        # check role and channel
        ALLOWED_CHANNELS = ["suggestions", "bug-report", "issues", "github"]
        ALLOWED_ROLES = ["Verified"]
        if await checks.roles(ctx, ALLOWED_ROLES) and await checks.channels(ctx, ALLOWED_CHANNELS):
            pass
        else:
            return

        try:
            # get repo
            repo = Repository()

            if len(arg) == 0:
                await ctx.send(f'You need to give a title to your request: `!request I want that`')
            else:
                repo.create_issue(" ".join(arg), f'Created by {ctx.author.display_name}', "request")
                await ctx.send(f'Your request has been reported. Thank you.')

        except BaseException as e:
            await ctx.send(f'Failed to create the issue: {e}')
