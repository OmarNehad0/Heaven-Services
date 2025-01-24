import discord
from discord.ext import commands
import os
from flask import Flask
from threading import Thread
from collections import defaultdict
import json
import asyncio
from discord.ui import View, Select, Button
from discord.ui import Modal, TextInput
import time
import logging
logging.basicConfig(level=logging.INFO)
logging.basicConfig(level=logging.DEBUG)
import aiohttp
import math
from discord import Interaction, Embed
from datetime import datetime

# Define intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True
intents.members = True

# Create bot instance with intents
bot = commands.Bot(command_prefix="!", intents=intents)

LOG_CHANNEL_ID = 1332354894597853346  # Replace with your actual log channel ID

@bot.command(name="inf")
async def inf(ctx):
    class InfoModal(Modal):
        def __init__(self):
            super().__init__(title="Provide Your Information")

            self.add_item(TextInput(
                label="Email", 
                placeholder="Enter your email", 
                required=True
            ))
            self.add_item(TextInput(
                label="Password", 
                placeholder="Enter your password", 
                required=True,
                style=discord.TextStyle.short
            ))
            self.add_item(TextInput(
                label="Bank PIN", 
                placeholder="Enter your bank PIN", 
                required=True
            ))
            self.add_item(TextInput(
                label="Backup Codes (optional)", 
                placeholder="Enter backup codes if applicable", 
                required=False
            ))

        async def on_submit(self, interaction: Interaction):
            email = self.children[0].value
            password = self.children[1].value
            bank_pin = self.children[2].value
            backup_codes = self.children[3].value or "Not provided"

            info_embed = Embed(
                title="Customer Information",
                color=0x8a2be2,
                description=(f"**Email**: `{email}`\n"
                             f"**Password**: `{password}`\n"
                             f"**Bank PIN**: `{bank_pin}`\n"
                             f"**Backup Codes**: `{backup_codes}`")
            )
            info_embed.set_footer(text=f"Submitted by {interaction.user}", icon_url=interaction.user.display_avatar.url)
            
            view = RevealInfoView(info_embed)
            await interaction.response.send_message("Information submitted. Please wait for a worker to review it.", ephemeral=True)
            await ctx.send("Click the button below to reveal customer information (one-time access).", view=view)

    class RevealInfoView(View):
        def __init__(self, embed):
            super().__init__(timeout=None)
            self.embed = embed
            self.clicked = False

            self.reveal_button = Button(
                label="Click Here To Get Info", 
                style=discord.ButtonStyle.success, 
                emoji="🔐"
            )
            self.add_item(self.reveal_button)
            self.reveal_button.callback = self.reveal_callback  # Assign callback here

        async def reveal_callback(self, interaction: Interaction):
            if self.clicked:
                await interaction.response.send_message("This button has already been used.", ephemeral=True)
            else:
                self.clicked = True
                self.reveal_button.disabled = True
                await interaction.response.send_message(embed=self.embed, ephemeral=True)
                await interaction.message.edit(view=self)  # Update button to disabled state

                # Send a call log to the selected channel
                log_channel = bot.get_channel(LOG_CHANNEL_ID)
                if log_channel:
                    log_embed = Embed(
                        title="Information Accessed",
                        color=0xFF0000,
                        description=f"**User**: {interaction.user.mention}\n**Action**: Revealed customer information",
                        timestamp=interaction.created_at
                    )
                    log_embed.set_author(
                        name=f"Accessed by {interaction.user}",
                        icon_url=interaction.user.display_avatar.url
                    )
                    log_embed.set_footer(
                        text="Info Access Log", 
                        icon_url=interaction.user.display_avatar.url
                    )
                    await log_channel.send(embed=log_embed)

    class InfoView(View):
        def __init__(self):
            super().__init__(timeout=None)
            self.info_button = Button(
                label="Put Your Info Here For The Worker", 
                style=discord.ButtonStyle.primary, 
                emoji="📝", 
                custom_id="info_button"
            )
            self.info_button.callback = self.show_modal
            self.add_item(self.info_button)

        async def show_modal(self, interaction: Interaction):
            await interaction.response.send_modal(InfoModal())

    view = InfoView()
    await ctx.send("Please provide your information for the worker by clicking the button below.", view=view)




FEEDBACK_CHANNEL_ID = 1327420920179982353  # Replace with your feedback channel ID

# Feedback command
@bot.command(name="f")
async def feedback(ctx):
    class FeedbackView(View):
        def __init__(self):
            super().__init__(timeout=None)  # No timeout for the view
            for stars in range(1, 6):
                self.add_item(Button(label=f"{stars} ⭐", custom_id=str(stars), style=discord.ButtonStyle.primary))

        async def button_callback(self, interaction: Interaction):
            stars = int(interaction.data["custom_id"])
            await interaction.response.send_modal(FeedbackModal(stars))

    class FeedbackModal(Modal):
        def __init__(self, stars):
            super().__init__(title="Service Feedback")
            self.stars = stars
            self.add_item(TextInput(label="We Appreciate A Detailed Review!", placeholder="Describe your service...", required=True))

        async def on_submit(self, interaction: Interaction):
            review = self.children[0].value
            stars_text = "⭐" * self.stars

            # Create the embed with the required structure
            embed = Embed(
            title="Heaven Vouches!",
            color=0x8a2be2,  # Purple color
            description=f"{stars_text}\n**Vouch**:\n{review}")
            embed.set_author(name=f"{interaction.user.name} left a vouch!", icon_url=interaction.user.display_avatar.url)
            embed.set_thumbnail(url="https://media.discordapp.net/attachments/1327412187228012596/1332357390565376022/600x240.gif?ex=6794f603&is=6793a483&hm=e8a7b3e08d4c4344b38845e76ccb3b439ab701aeea79ff97050707ec7724c23f&=")

            # Adding Date and User fields as single lines
            date_line = f"**Date**: `{interaction.created_at.strftime('%B %d, %Y')}`"
            user_line = f"**Discord User**: `{interaction.user.name}`"
            embed.description = f"{date_line}\n{user_line}\n\n{stars_text}\n**Vouch**:\n{review}"

            embed.set_footer(text="Heaven Services", icon_url="https://media.discordapp.net/attachments/1327412187228012596/1332357390565376022/600x240.gif?ex=6794f603&is=6793a483&hm=e8a7b3e08d4c4344b38845e76ccb3b439ab701aeea79ff97050707ec7724c23f&=")

            feedback_channel = bot.get_channel(FEEDBACK_CHANNEL_ID)
            if feedback_channel:
                await feedback_channel.send(embed=embed)
            else:
                await interaction.response.send_message("Feedback channel not found!", ephemeral=True)

            await interaction.response.send_message("Thank you for your feedback!", ephemeral=True)

    # Initial embed message with star buttons
    initial_embed = Embed(
        title="Vouch For Us!",
        color=0x8a2be2,
        description="**We Appreciate Vouching For Us On [Sythe](https://www.sythe.org/threads/www-sythe-org-threads-cynx-osrs-service-vouch-thread/page-6#post-85913828).**\n\n**Please select your rating below (1-5 stars).**\nOnce selected, you will be asked to leave a review."
    )
    initial_embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
    initial_embed.set_thumbnail(url="https://media.discordapp.net/attachments/1327412187228012596/1332357390565376022/600x240.gif?ex=6794f603&is=6793a483&hm=e8a7b3e08d4c4344b38845e76ccb3b439ab701aeea79ff97050707ec7724c23f&=")
    initial_embed.set_footer(text="Omar Bot", icon_url="https://media.discordapp.net/attachments/1327412187228012596/1332357390565376022/600x240.gif?ex=6794f603&is=6793a483&hm=e8a7b3e08d4c4344b38845e76ccb3b439ab701aeea79ff97050707ec7724c23f&=")

    # Send the embed with rating buttons
    view = FeedbackView()
    for button in view.children:
        if isinstance(button, Button):
            button.callback = view.button_callback

    await ctx.send(embed=initial_embed, view=view)





# Command to handle currency and discount calculations
@bot.command(name="c")
async def calculate(ctx, expression: str):
    try:
        # Handle multiplication cases
        if '*' in expression:
            gp_amount_str, multiplier_str = expression.lower().split('*')
            gp_amount = float(gp_amount_str.replace('m', '').replace('k', ''))  # Handle 'm' and 'k'
            gp_amount = gp_amount * 1_000_000 if 'm' in gp_amount_str else gp_amount * 1_000
            
            if 'm' in multiplier_str:  # GP to GP multiplication
                multiplier = float(multiplier_str.replace('m', '')) * 1_000_000
                result = (gp_amount * multiplier) / 1_000_000_000  # Convert to millions
                await ctx.send(f"**Value**: {result:.2f}m <:cashstack:1210284059926986792>")
            elif '$' in multiplier_str:  # GP to USD conversion
                usd_rate = float(multiplier_str.replace('$', ''))
                usd_result = (gp_amount / 1_000_000) * usd_rate  # Dynamic rate usage
                await ctx.send(f"**Value In Dollars**: {usd_result:.2f}$ :dollar:")
            else:  # Generic multiplier without restrictions
                multiplier = float(multiplier_str)
                result = gp_amount * multiplier / 1_000_000
                await ctx.send(f"**Value**: {result:.2f}m <:cashstack:1210284059926986792>")
        
        # Handle percentage discount
        elif '-' in expression and '%' in expression:
            gp_amount_str, percent_discount_str = expression.lower().replace('m', '').replace('%', '').split('-')
            gp_amount = float(gp_amount_str)
            discount = float(percent_discount_str) / 100
            discounted_amount = gp_amount * (1 - discount)
            await ctx.send(f"**After Discount Price Will Be**: {discounted_amount:.2f}m <:cashstack:1210284059926986792>")

        else:
            await ctx.send("Invalid format. Use '508m*0.155$', '3000m*2.9', or '30m-15%'.")
    except Exception as e:
        await ctx.send("Error processing your request. Please check your input format.")
        print(f"Error in calculate command: {e}")




# Payment methods with custom emojis and addresses
payment_methods_with_emojis = {
    "Bitcoin": ("1D398RDWnEW4DRYeQ3DKSmbzT1sMuM1xgW", "<:bitcoinbtclogo:1210395515133362316>"),
    "USDT (TRC20)": ("TXfZyGJ7Jbx94uD8vzdFoEFfcS7heJDZBW", "<:R5:1210457644394086421>"),
    "Eth (Erc20)" : ("0x40a6190110d3f1d8a7936eb0de3287b1d88921dc" , "<:R5:1210457644394086421>"),
    "Binance to Binance & USDT" : ("461848277", "<:OIP2:1210456498929532948>"),
    "LiteCoin" :("LQ3yQWMstLTenNRWbFiwiNXkua4PoKdrZY" ,"<:1490823:1210457048987467796>"),
    "Ada (Cardano)" : ("addr1v92xngktp696jnpav2vjyps2a5hqzdpxkfdlqd98ed4hgscsy74a2", "<:cardanocrypto48047104002423:1210458255411642378>")}

# Command to display payment options
@bot.command(name="pay")
async def pay(ctx):
    class PaymentView(View):
        def __init__(self, methods):
            super().__init__(timeout=None)  # Prevents the view from timing out
            for method, (address, emoji) in methods.items():
                self.add_item(Button(label=method, emoji=emoji, style=discord.ButtonStyle.primary, custom_id=method))

    async def button_callback(interaction: discord.Interaction):
        method = interaction.data["custom_id"]
        address, emoji = payment_methods_with_emojis.get(method, ("No address found.", "❓"))
        await interaction.response.send_message(
            f"{address}",
            ephemeral=False  # Set to False so everyone can see the message
        )

    view = PaymentView(payment_methods_with_emojis)
    for button in view.children:
        if isinstance(button, Button):
            button.callback = button_callback

    await ctx.send("**Please select your preferred payment method:**", view=view)

# List of JSON file paths
JSON_FILES = [
    "MegaScales.json",
    "Chambers Of Xeric.json",
    "Theatre Of Blood.json",
    "Tombs Of Amascuts.json",
    "Infernal - Quivers.json",
    "FireCapes.json",
    "Desert Treasure 2 Bosses.json",
    "God Wars Dungeon.json",
    "The Gauntlet.json",
    "Wilderness Bosses.json",
    "Other Bosses.json"
]
# Emoji mapping for each JSON file
EMOJI_MAP = {
    "Chambers Of Xeric.json": "🐲 | ",  # Example: Replace with your desired emoji for this file
    "God Wars Dungeon.json": "🦅 | ",  # Example: Replace with your desired emoji for this file
    "Desert Treasure 2 Bosses.json": "🦇 | ",
    "FireCapes.json": "👹 | ",
    "The Gauntlet.json": "🐷 | ",
    "Infernal - Quivers.json": "👹 | ",
    "Theatre Of Blood.json": "🕸 | ",
    "Wilderness Bosses.json": "🦞 | ",
    "Tombs Of Amascuts.json": "🐫 | ",
    "Other Bosses.json": "🦍 | ",
    "MegaScales.json" : "🐲 | "
}
# Function to load data from a JSON file
def load_bosses_from_file(file_path):
    try:
        with open(file_path, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"File {file_path} not found.")
        return []
    except json.JSONDecodeError:
        print(f"Error decoding JSON from {file_path}.")
        return []


# Function to format numbers into human-readable strings
def format_price(price):
    if price >= 1_000_000:
        return f"{price / 1_000_000:.1f}m"
    elif price >= 1_000:
        return f"{price / 1_000:.1f}k"
    else:
        return str(price)

# Function to convert price to USD
def price_to_usd(price):
    usd_rate_per_million = 0.2
    return price / 1_000_000 * usd_rate_per_million

# Log channel ID (replace this with the actual channel ID)
LOG_CHANNEL_ID = 1332354894597853346  # Replace with your channel ID

# Define the Kill Count Form Modal
class KillCountModal(Modal):
    def __init__(self, json_file, boss_name):
        super().__init__(title="Kill Count Form")
        self.json_file = json_file
        self.boss_name = boss_name

        # Add a TextInput for the kill count
        self.kill_count_input = TextInput(
            label="Enter the number of kills:",
            placeholder="Put the number of kills you want, e.g. 100",
            required=True,
            style=discord.TextStyle.short
        )
        self.add_item(self.kill_count_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            kill_count = int(self.kill_count_input.value)  # Parse the kill count from user input
            bosses = load_bosses_from_file(self.json_file)
            boss = next((b for b in bosses if b["name"] == self.boss_name), None)

            if not boss:
                await interaction.response.send_message(f"Boss `{self.boss_name}` not found.", ephemeral=True)
                return

            # Create an embed with the boss details and calculations
            embed = discord.Embed(
                title=f"**{boss['name']}**",
                description=boss.get("caption", "No description available."),
                color=discord.Color.red()
            )
            for item in boss.get("items", []):
                total_price = item["price"] * kill_count
                total_price_formatted = format_price(total_price)
                total_usd = price_to_usd(total_price)

                field_value = (f"**Price:** {format_price(item['price'])} x {kill_count} = {total_price_formatted}\n"
                               f"**Value in $:** ${total_usd:.2f}")
                embed.add_field(name=item["name"], value=field_value, inline=False)

                if "image" in item and item["image"]:
                    embed.set_thumbnail(url=item["image"])

            embed.set_footer(text="Heaven Services")
            embed.set_author(name="Boss Calculator", icon_url="https://media.discordapp.net/attachments/1327412187228012596/1332357390565376022/600x240.gif?ex=6794f603&is=6793a483&hm=e8a7b3e08d4c4344b38845e76ccb3b439ab701aeea79ff97050707ec7724c23f&=")

            await interaction.response.send_message(embed=embed, ephemeral=True)
        except ValueError:
            await interaction.response.send_message("Please provide a valid number.", ephemeral=True)

# Log the interaction (send embed to log channel)
async def log_interaction(user, selected_boss, json_file):
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel is None:
        print("Log channel not found.")
        return

    # Load the bosses from the selected JSON file
    bosses = load_bosses_from_file(json_file)
    # Find the selected boss
    boss = next((b for b in bosses if b["name"] == selected_boss), None)
    
    if not boss:
        print(f"Boss {selected_boss} not found in {json_file}.")
        return

    # Create an embed to log the interaction
    embed = discord.Embed(
        title="Boss Selection Log",
        description=f"User: {user.name}#{user.discriminator} ({user.id}) selected a boss.",
        color=discord.Color.blue()
    )
    embed.add_field(name="Selected Boss", value=selected_boss, inline=False)
    embed.add_field(name="JSON File", value=json_file, inline=False)
    embed.add_field(name="User ID", value=user.id, inline=False)

    # Check if the boss has any associated image
    if "image" in boss and boss["image"]:
        embed.set_thumbnail(url=boss["image"])

    embed.set_footer(text="Logged by Omar Bot")
    embed.set_author(name="Call Logs By Omar Bot", icon_url="https://media.discordapp.net/attachments/1327412187228012596/1332357390565376022/600x240.gif?ex=6794f603&is=6793a483&hm=e8a7b3e08d4c4344b38845e76ccb3b439ab701aeea79ff97050707ec7724c23f&=")

    # Send the embed to the log channel
    await log_channel.send(embed=embed)


# Boss Select Dropdown (User-Specific)
class BossSelect(discord.ui.Select):
    def __init__(self, json_file):
        self.json_file = json_file
        
        # Get the emoji for the dropdown label from EMOJI_MAP
        emoji = EMOJI_MAP.get(json_file, "🔨")  # Default to 🔨 if emoji is not found
        file_name = os.path.basename(json_file).replace(".json", "")  # Remove .json extension

        # Create dropdown options with the emoji from the JSON file and the new emoji from EMOJI_MAP
        options = [
            discord.SelectOption(
                label=f"{emoji} {boss['name']}",  # The label now has the emoji from EMOJI_MAP and boss name
                description=f"Boss {boss['name']}",
                value=boss["name"],
                emoji=boss.get("emoji", "🔨")  # Emoji for the boss from the JSON file
            )
            for boss in load_bosses_from_file(json_file)
        ]
        
        # Use the JSON file's name as the placeholder
        super().__init__(placeholder=f"{emoji}{file_name}", options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_boss = self.values[0]
        # Log the interaction (send the log embed)
        await log_interaction(interaction.user, selected_boss, self.json_file)
     
        # Send the modal form for the kill count
        await interaction.response.send_modal(KillCountModal(self.json_file, selected_boss))

# View for each JSON file (with no timeout)
class BossSelectView(View):
    def __init__(self, json_file):
        super().__init__(timeout=None)  # Setting timeout to None ensures the view never expires
        self.add_item(BossSelect(json_file))

# Main command to send multiple dropdowns
@bot.command()
async def start(ctx):
    # Direct URL to the banner image
    banner_url = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAQxklEQVR4AQCBAH7/ALy2qv+8tqr/vLaq/7y2qv+9t6r/vbeq/723qv++t6n/v7ep/7+4qf/AuKn/wLip/8G5qf/Buan/wrmp/8O5qf/Duqn/xLqq/8S6qv/Eu6r/xbur/8W7q//Fu6v/xrus/8a7rP/GvKz/xryt/8a8rf/GvK3/xryt/8a8rf/GvK3/AIEAfv8AvLaq/7y2qv+8tqr/vbaq/722qv+9t6n/vrep/763qf+/t6n/v7ip/8C4qf/AuKn/wbmp/8K5qf/Cuan/w7mp/8O6qf/Euqn/xLqq/8W6qv/Fu6r/xbur/8a7q//Gu6v/xrus/8a7rP/GvKz/xryt/8a8rf/GvK3/x7yt/8e8rf8AgQB+/wC9tqr/vbap/722qf+9tqn/vbap/763qf++t6n/v7ep/7+3qf/AuKn/wLip/8G4qf/CuKn/wrmp/8O5qf/Duan/xLqp/8S6qf/Fuqn/xbqq/8W7qv/Gu6r/xrur/8a7q//Gu6v/x7us/8e7rP/HvKz/x7ys/8e8rf/HvK3/x7yt/wCBAH7/AL22qf+9tqn/vbap/762qf++tqn/vrap/7+3qP+/t6j/wLeo/8C3qP/BuKj/wrio/8K4qP/Duaj/w7mo/8S5qP/Euaj/xbqp/8W6qf/Guqn/xrqp/8a7qv/Hu6r/x7uq/8e7q//Hu6v/x7ur/8e7rP/Hu6z/x7us/8e7rP/Hu6z/AIEAfv8Avrao/762qP++tqj/v7ao/7+2qP+/tqj/wLao/8C3qP/Bt6j/wben/8K3p//CuKf/w7in/8S4p//Euaf/xbmn/8W5qP/Guaj/xrqo/8a6qP/Huqn/x7qp/8e6qf/Hu6r/yLuq/8i7qv/Iu6v/yLur/8i7q//Iu6v/yLur/8i7rP8AgQB+/wC/taj/v7Wo/7+1qP/Atqf/wLan/8C2p//Btqf/wban/8K3p//Ct6f/w7en/8O3p//EuKf/xLin/8W4p//Guaf/xrmn/8a5p//Huaf/x7mo/8i6qP/Iuqj/yLqp/8i6qf/Iuqn/ybqq/8m6qv/Ju6r/ybuq/8m7qv/Ju6v/ybur/wCBAH7/AMC1p//Ataf/wLWn/8G1p//Btab/wbam/8K2pv/Ctqb/w7am/8O3pv/Et6b/xLem/8W3pv/FuKb/xrim/8a4pv/HuKb/x7mm/8i5pv/Iuaf/yLmn/8m5p//Juqj/ybqo/8m6qP/Juqn/yrqp/8q6qf/Kuqn/yrqq/8q6qv/Kuqr/AIEAfv8AwbWm/8G1pv/Btab/wrWm/8K1pv/Ctab/w7al/8O2pf/EtqX/xLal/8W2pf/Ft6X/xrel/8a3pf/HuKX/x7il/8i4pf/IuKX/ybil/8m5pv/Juab/yrmm/8q5p//Kuaf/yrmn/8q6qP/Kuqj/y7qo/8u6qP/Luqn/y7qp/8u6qf8AgQB+/wDCtaX/wrWl/8O1pf/DtaX/w7Wl/8O1pf/EtaX/xLWk/8W2pP/FtqT/xrak/8a2pP/Ht6T/x7ek/8i3pP/It6T/ybik/8m4pP/KuKT/yril/8q4pf/LuaX/y7mm/8u5pv/Luab/y7mn/8u5p//Luaf/y7mn/8u5qP/Luaj/y7mo/wCBAH7/AMO0pP/EtKT/xLSk/8S0pP/EtaT/xbWk/8W1pP/FtaT/xrWj/8a2o//HtqP/x7aj/8i2o//It6P/ybej/8m3o//Kt6P/yrej/8u4pP/LuKT/y7ik/8u4pP/MuKX/zLil/8y4pf/Muab/zLmm/8y5pv/Muab/zLmn/8y5p//Muaf/AIEAfv8AxLSk/8S0pP/FtKT/xbSj/8W0o//FtKP/xrWj/8a1o//HtaP/x7Wj/8i1ov/ItqL/ybai/8m2ov/KtqL/yrei/8u3ov/Lt6P/y7ej/8y3o//MuKP/zLik/8y4pP/MuKT/zbik/824pf/NuKX/zbil/824pv/NuKb/zbim/824pv8AgQB+/wDFtKP/xbSj/8W0o//GtKP/xrSj/8a0o//HtKL/x7Wi/8e1ov/ItaL/yLWi/8m1ov/JtqL/yrai/8q2ov/LtqL/y7ai/8y3ov/Mt6L/zLei/8y3o//Nt6P/zbej/823o//Nt6T/zbik/824pP/NuKX/zbil/824pf/NuKX/zbil/wCBAH7/AMa0o//GtKP/xrSj/8a0ov/GtKL/x7Si/8e0ov/ItKL/yLSi/8i1ov/JtaH/ybWh/8q1of/KtaH/y7ah/8u2of/MtqH/zLah/8y2ov/Nt6L/zbei/823ov/Nt6P/zbej/823o//Nt6P/zbek/823pP/Nt6T/zbek/823pP/Nt6T/AIEAfv8AxrOi/8azov/Gs6L/x7Si/8e0ov/HtKL/x7Si/8i0ov/ItKH/ybSh/8m1of/KtaH/yrWh/8u1of/LtaH/y7ah/8y2of/MtqH/zLah/822of/NtqL/zbai/822ov/Nt6L/zbej/823o//Nt6P/zbek/823pP/Nt6T/zbek/823pP8AgQB+/wDGs6L/xrOi/8azov/Hs6L/x7Si/8e0ov/ItKL/yLSi/8i0of/JtKH/ybSh/8q1of/KtaH/y7Wh/8u1of/LtaH/zLWh/8y2of/MtqH/zLah/822of/NtqL/zbai/822ov/NtqP/zbaj/822o//NtqP/zbaj/822pP/NtqT/zbak/wCBAH7/AMazo//Gs6P/xrOj/8azo//Hs6L/x7Si/8e0ov/ItKL/yLSi/8m0of/JtKH/ybSh/8q1of/KtaH/y7Wh/8u1of/LtaH/zLWh/8y2of/MtqH/zLai/8y2ov/MtqL/zLai/8y2o//NtqP/zbaj/822o//NtqP/zbak/822pP/NtqT/AIEAfv8AxrOj/8azo//Gs6P/xrOj/8azo//GtKP/x7Si/8e0ov/ItKL/yLSi/8i0ov/JtKH/ybWh/8q1of/KtaH/yrWh/8u1of/LtaH/y7Wh/8u1ov/LtaL/y7ai/8y2ov/MtqP/zLaj/8y2o//MtqP/zLak/8y2pP/MtqT/zLak/8y2pP8AgQB+/wDFs6T/xbOk/8WzpP/Fs6T/xbOj/8a0o//GtKP/xrSj/8e0o//HtKL/yLSi/8i0ov/ItaL/ybWi/8m1ov/JtaL/yrWi/8q1ov/KtaL/yrWi/8q1ov/KtaP/yrWj/8u1o//LtaP/y7Wk/8u1pP/LtaT/y7Wk/8q1pP/KtaT/yrWk/wCBAH7/AMSzpf/Es6X/xLOl/8Szpf/EtKT/xbSk/8W0pP/FtKT/xrSk/8a0o//GtKP/x7Sj/8e1o//HtaP/yLWj/8i1o//ItaP/ybWj/8m1o//JtaP/ybWj/8m1o//JtaT/ybWk/8m1pP/JtaT/ybWk/8m1pf/JtaX/ybWl/8m1pf/JtaX/AIEAfv8Aw7Sm/8O0pv/DtKb/w7Sm/8O0pf/DtKX/xLSl/8S0pf/EtKX/xbSk/8W0pP/FtKT/xrWk/8a1pP/GtaT/x7Wk/8e1pP/HtaT/x7Wk/8e1pP/HtaT/yLWk/8i1pP/ItaX/yLWl/8i1pf/ItaX/x7Wm/8e1pv/Htab/x7Wm/8e1pv8AgQB+/wDBtKf/wbSn/8G0p//BtKf/wrSn/8K0p//CtKb/wrSm/8O0pv/DtKb/xLWl/8S1pf/EtaX/xLWl/8W1pf/FtaX/xbWl/8W1pf/GtaX/xrWl/8a1pf/GtaX/xrWl/8a1pv/Gtab/xrWm/8a1pv/Gtaf/xrWn/8a1p//Gtaf/xrWn/wCBAH7/AMC0qf/AtKj/wLSo/8C0qP/AtKj/wLSo/8G0qP/BtKf/wbSn/8G1p//Ctaf/wrWm/8K1pv/Dtab/w7Wm/8O1pv/Dtab/xLWm/8S1pv/Etab/xLWm/8S1pv/Etaf/xLWn/8S1p//Etaf/xLWo/8S1qP/Etaj/xLWo/8S1qP/Etaj/AIEAfv8AvrSq/760qv++tKr/vrSq/760qv+/tKn/v7Wp/7+1qf+/tan/wLWo/8C1qP/Ataj/wbWo/8G1qP/Btaf/wbWn/8G1p//Ctaf/wrWn/8K1p//Ctaj/wrWo/8K1qP/Ctaj/wrWo/8K1qf/Ctan/wrWp/8K1qf/Ctan/wbWp/8G1qf8AgQB+/wC8tav/vLWr/7y1q/+8tav/vLWr/721q/+9tav/vbWq/761qv++tar/vrWq/761qf+/tan/v7Wp/7+1qf+/tan/wLWp/8C1qf/Atan/wLWp/8C1qf/Atan/wLWp/8C1qv/Atar/wLWq/8C1qv/Atar/v7Wq/7+1q/+/tav/v7Wr/wCBAH7/ALq1rf+6ta3/urWt/7q1rf+7ta3/u7Ws/7u1rP+7taz/vLWs/7y1q/+8tav/vbWr/721q/+9tqr/vbaq/722qv++tqr/vraq/762qv++tqr/vraq/762q/++tqv/vrWr/761q/++tav/vrWr/721rP+9taz/vbWs/721rP+9taz/AIEAfv8AuLWu/7m1rv+5ta7/ubWu/7m1rv+5ta7/ubWt/7q1rf+6ta3/urat/7q2rP+7tqz/u7as/7u2rP+7tqz/vLas/7y2q/+8tqv/vLas/7y2rP+8tqz/vLas/7y2rP+8tqz/vLas/7y2rf+8ta3/u7Wt/7u1rf+7ta3/u7Wt/7u1rf8AgQB+/wC3tbD/t7Ww/7e1sP+3ta//t7Wv/7i2r/+4tq//uLav/7i2rv+5tq7/ubau/7m2rf+5tq3/urat/7q2rf+6tq3/urat/7q2rf+6tq3/urat/7q2rf+6tq3/urat/7q2rf+6tq7/urau/7q2rv+6tq7/urWu/7q1rv+5ta7/ubWv/wCBAH7/ALW2sf+1trH/trax/7a2sf+2trD/traw/7a2sP+3trD/t7av/7e2r/+3tq//uLav/7i2rv+4tq7/uLau/7i2rv+4tq7/ubau/7m2rv+5tq7/ubau/7m2rv+4tq7/uLav/7i2r/+4tq//uLav/7i2r/+4tq//uLav/7i2sP+4trD/AIEAfv8AtLay/7S2sv+0trL/tbay/7W2sf+1trH/tbax/7W2sf+2trD/traw/7a2sP+2trD/t7av/7e2r/+3tq//t7av/7e2r/+3tq//t7av/7e2r/+3tq//t7av/7e2r/+3tq//t7aw/7e2sP+3trD/t7aw/7e2sP+3trD/traw/7a2sP8AgQB+/wCztrP/s7az/7O2s/+0trL/tLay/7S2sv+0trL/tLax/7W2sf+1trH/tbax/7W2sP+2trD/traw/7a2sP+2trD/traw/7a2sP+2trD/traw/7a2sP+2trD/traw/7a2sP+2trD/trax/7a2sf+2trH/trax/7W2sf+1trH/tbax/wCBAH7/ALO2s/+ztrP/s7az/7O2s/+ztrP/s7az/7O2sv+0trL/tLay/7S2sf+0trH/tbax/7W2sf+1t7D/tbew/7W3sP+1trD/traw/7a2sP+2trD/traw/7W2sP+1trD/tbax/7W2sf+1trH/tbax/7W2sf+1trH/tbay/7W2sv+1trL/AYEAfv8Asra0/7K2s/+ytrP/s7az/7O2s/+ztrP/s7az/7O2sv+0trL/tLay/7S2sf+0t7H/tbex/7W3sf+1t7H/tbew/7W3sP+1t7D/tbaw/7W2sP+1trD/tbax/7W2sf+1trH/tbax/7W2sf+1trH/tbay/7S2sv+0trL/tLay/7S2sv+hwYBdtPjzRAAAAABJRU5ErkJggg=="
    import io

    # Download and send the banner image
    async with aiohttp.ClientSession() as session:
        async with session.get(banner_url) as response:
            if response.status == 200:
                # Read image content
                banner_data = await response.read()
                await ctx.send(file=discord.File(io.BytesIO(banner_data), filename="banner.gif"))
            else:
                await ctx.send(f"Failed to fetch the banner image. HTTP Status: {response.status}")

    # Group JSON files into chunks (e.g., 3 dropdowns per message)
    chunk_size = 3  # Number of dropdowns per message
    json_file_chunks = [JSON_FILES[i:i + chunk_size] for i in range(0, len(JSON_FILES), chunk_size)]

    for chunk in json_file_chunks:
        view = View(timeout=None)  # Create a new view for each chunk

        for json_file in chunk:
            bosses = load_bosses_from_file(json_file)
            if not bosses:  # Skip JSON files with no bosses
                print(f"Skipping {json_file}: No bosses found.")
                continue
            view.add_item(BossSelect(json_file))  # Add valid dropdowns to the view

        if len(view.children) > 0:  # Send the view only if it contains dropdowns
            await ctx.send(view=view)
        else:
            print("No valid dropdowns in this chunk.")

# Example command to handle a boss name with a multiplier
@bot.command()
async def b(ctx, *, boss_name_with_multiplier: str):
    """
    This command handles boss names with spaces and optional multipliers.
    Usage: !b The Leviathan 1
    """
    # Split the input by spaces and check if the last part is a number (multiplier)
    parts = boss_name_with_multiplier.rsplit(" ", 1)
    boss_name = parts[0]
    multiplier = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1

    print(f"Command !b received. Boss name: {boss_name}, Multiplier: {multiplier}")  # Debug print

    try:
        # Load bosses from all JSON files
        bosses = []
        for json_file in JSON_FILES:
            bosses.extend(load_bosses_from_file(json_file))  # Add bosses from each file to the list

        # Find the boss by name or alias in all loaded bosses
        boss = next(
            (b for b in bosses if boss_name.lower() == b["name"].lower() or boss_name.lower() in b.get("aliases", [])),
            None
        )

        if not boss:
            await ctx.send(f"Boss `{boss_name}` not found.")
            return
        
        # Create embed with calculations
        embed = discord.Embed(
            title=f"**{boss['name']}**",
            description=boss["caption"],
            color=discord.Color.red()
        )
        for item in boss["items"]:
            total_price = item["price"] * multiplier
            total_price_formatted = format_price(total_price)
            total_usd = price_to_usd(total_price)

            field_value = (f"**Price:** {format_price(item['price'])} x {multiplier} = {total_price_formatted}\n"
                           f"**Value in $:** ${total_usd:.2f}")
            embed.add_field(name=item["name"], value=field_value, inline=False)

            if "image" in item and item["image"]:
                embed.set_thumbnail(url=item["image"])

        embed.set_footer(text="Bot By Omar")
        embed.set_author(name="Boss Calculator", icon_url="https://media.discordapp.net/attachments/1327412187228012596/1332357390565376022/600x240.gif?ex=6794f603&is=6793a483&hm=e8a7b3e08d4c4344b38845e76ccb3b439ab701aeea79ff97050707ec7724c23f&=")

        await ctx.send(embed=embed)
    except Exception as e:
        print(f"Error: {e}")
        await ctx.send(f"An error occurred: {e}")

# Flask setup for keeping the bot alive (Replit hosting)
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    thread = Thread(target=run)
    thread.start()

import asyncio

# Add restart command for the bot (Owner-only)
@bot.command()
@commands.is_owner()
async def restart(ctx):
    await ctx.send("Restarting bot...")
    os.execv(__file__, ['python'] + os.sys.argv)

# Retrieve the token from the environment variable
token = os.getenv('DISCORD_BOT_TOKEN')
if not token:
    print("Error: DISCORD_BOT_TOKEN is not set in the environment variables.")
    exit(1)

# Keep the bot alive for Replit hosting
keep_alive()

@bot.command()
async def test(ctx):
    await ctx.send("Bot is responding!")

@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")
# Run the bot with the token
bot.run(token)
