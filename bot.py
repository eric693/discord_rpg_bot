import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from datetime import datetime, timedelta
from typing import Optional, List
import asyncio

# 初始化機器人
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# 數據文件路徑
DATA_DIR = "data"
SHOPS_FILE = f"{DATA_DIR}/shops.json"
USERS_FILE = f"{DATA_DIR}/users.json"
CHARACTERS_FILE = f"{DATA_DIR}/characters.json"
CHECKIN_FILE = f"{DATA_DIR}/checkins.json"
INCOME_ROLES_FILE = f"{DATA_DIR}/income_roles.json"

# 確保數據目錄存在
os.makedirs(DATA_DIR, exist_ok=True)

# ==================== 數據管理函數 ====================

def load_json(filepath, default=None):
    """載入JSON文件"""
    if default is None:
        default = {}
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default

def save_json(filepath, data):
    """保存JSON文件"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_shops():
    """獲取所有商店數據"""
    return load_json(SHOPS_FILE, {})

def save_shops(shops):
    """保存商店數據"""
    save_json(SHOPS_FILE, shops)

def get_users():
    """獲取所有用戶數據"""
    return load_json(USERS_FILE, {})

def save_users(users):
    """保存用戶數據"""
    save_json(USERS_FILE, users)

def get_characters():
    """獲取所有角色數據"""
    return load_json(CHARACTERS_FILE, {})

def save_characters(characters):
    """保存角色數據"""
    save_json(CHARACTERS_FILE, characters)

def get_checkins():
    """獲取簽到記錄"""
    return load_json(CHECKIN_FILE, {})

def save_checkins(checkins):
    """保存簽到記錄"""
    save_json(CHECKIN_FILE, checkins)

def get_income_roles():
    """獲取收入身份組"""
    return load_json(INCOME_ROLES_FILE, {})

def save_income_roles(roles):
    """保存收入身份組"""
    save_json(INCOME_ROLES_FILE, roles)

def init_user(user_id: str):
    """初始化用戶數據"""
    users = get_users()
    if user_id not in users:
        users[user_id] = {
            "balance": 0,
            "inventory": {},
            "character": None
        }
        save_users(users)
    return users[user_id]

# ==================== 商店相關視圖 ====================

class CreateShopModal(discord.ui.Modal, title='創建商店'):
    shop_name = discord.ui.TextInput(
        label='商店名稱',
        placeholder='輸入你的商店名稱...',
        required=True,
        max_length=50
    )
    
    currency_name = discord.ui.TextInput(
        label='貨幣名稱',
        placeholder='例如: 金幣、元寶、鑽石...',
        required=True,
        max_length=20
    )
    
    currency_emoji = discord.ui.TextInput(
        label='貨幣表情符號',
        placeholder='例如: 💰 或 :coin:',
        required=False,
        max_length=50
    )
    
    banner_url = discord.ui.TextInput(
        label='商店橫幅圖片URL',
        placeholder='輸入圖片連結（可選）',
        required=False,
        style=discord.TextStyle.long
    )
    
    description = discord.ui.TextInput(
        label='商店描述',
        placeholder='介紹一下你的商店...',
        required=False,
        style=discord.TextStyle.long,
        max_length=200
    )

    async def on_submit(self, interaction: discord.Interaction):
        shops = get_shops()
        user_id = str(interaction.user.id)
        
        if user_id not in shops:
            shops[user_id] = {}
        
        shop_id = f"shop_{len(shops[user_id]) + 1}"
        shops[user_id][shop_id] = {
            "name": self.shop_name.value,
            "owner": user_id,
            "currency_name": self.currency_name.value,
            "currency_emoji": self.currency_emoji.value or "💰",
            "banner_url": self.banner_url.value or None,
            "description": self.description.value or "這是一家商店",
            "items": {},
            "created_at": datetime.now().isoformat()
        }
        
        save_shops(shops)
        
        embed = discord.Embed(
            title="✅ 商店創建成功！",
            description=f"**{self.shop_name.value}** 已成功創建",
            color=discord.Color.green()
        )
        embed.add_field(name="商店ID", value=shop_id, inline=False)
        embed.add_field(name="貨幣", value=f"{self.currency_emoji.value} {self.currency_name.value}", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class AddItemModal(discord.ui.Modal, title='添加商品'):
    item_name = discord.ui.TextInput(
        label='商品名稱',
        placeholder='輸入商品名稱...',
        required=True,
        max_length=50
    )
    
    price = discord.ui.TextInput(
        label='價格',
        placeholder='輸入價格（0表示非賣品）',
        required=True,
        max_length=10
    )
    
    category = discord.ui.TextInput(
        label='類別',
        placeholder='例如: 武器、防具、消耗品...',
        required=True,
        max_length=30
    )
    
    description = discord.ui.TextInput(
        label='商品描述',
        placeholder='描述這個商品...',
        required=True,
        style=discord.TextStyle.long,
        max_length=500
    )
    
    image_url = discord.ui.TextInput(
        label='商品圖片URL',
        placeholder='輸入圖片連結（可選）',
        required=False,
        style=discord.TextStyle.long
    )
    
    def __init__(self, shop_id: str):
        super().__init__()
        self.shop_id = shop_id

    async def on_submit(self, interaction: discord.Interaction):
        try:
            price = int(self.price.value)
        except ValueError:
            await interaction.response.send_message("❌ 價格必須是數字！", ephemeral=True)
            return
        
        shops = get_shops()
        user_id = str(interaction.user.id)
        
        if user_id not in shops or self.shop_id not in shops[user_id]:
            await interaction.response.send_message("❌ 找不到該商店！", ephemeral=True)
            return
        
        item_id = f"item_{len(shops[user_id][self.shop_id]['items']) + 1}"
        shops[user_id][self.shop_id]['items'][item_id] = {
            "name": self.item_name.value,
            "price": price,
            "category": self.category.value,
            "description": self.description.value,
            "image_url": self.image_url.value or None,
            "usable": True,
            "resellable": True,
            "consumable": True,
            "use_description": "",
            "created_at": datetime.now().isoformat()
        }
        
        save_shops(shops)
        
        embed = discord.Embed(
            title="✅ 商品添加成功！",
            description=f"**{self.item_name.value}** 已添加到商店",
            color=discord.Color.green()
        )
        embed.add_field(name="價格", value=f"{price} {shops[user_id][self.shop_id]['currency_emoji']}", inline=True)
        embed.add_field(name="類別", value=self.category.value, inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class ItemSettingsView(discord.ui.View):
    def __init__(self, shop_id: str, item_id: str, owner_id: str):
        super().__init__(timeout=300)
        self.shop_id = shop_id
        self.item_id = item_id
        self.owner_id = owner_id
    
    @discord.ui.button(label='可使用', style=discord.ButtonStyle.gray, custom_id='toggle_usable')
    async def toggle_usable(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.owner_id:
            await interaction.response.send_message("❌ 只有商店擁有者可以修改設定！", ephemeral=True)
            return
        
        shops = get_shops()
        item = shops[self.owner_id][self.shop_id]['items'][self.item_id]
        item['usable'] = not item['usable']
        save_shops(shops)
        
        button.style = discord.ButtonStyle.green if item['usable'] else discord.ButtonStyle.red
        await interaction.response.edit_message(view=self)
    
    @discord.ui.button(label='可轉售', style=discord.ButtonStyle.gray, custom_id='toggle_resellable')
    async def toggle_resellable(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.owner_id:
            await interaction.response.send_message("❌ 只有商店擁有者可以修改設定！", ephemeral=True)
            return
        
        shops = get_shops()
        item = shops[self.owner_id][self.shop_id]['items'][self.item_id]
        item['resellable'] = not item['resellable']
        save_shops(shops)
        
        button.style = discord.ButtonStyle.green if item['resellable'] else discord.ButtonStyle.red
        await interaction.response.edit_message(view=self)
    
    @discord.ui.button(label='消耗型', style=discord.ButtonStyle.gray, custom_id='toggle_consumable')
    async def toggle_consumable(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.owner_id:
            await interaction.response.send_message("❌ 只有商店擁有者可以修改設定！", ephemeral=True)
            return
        
        shops = get_shops()
        item = shops[self.owner_id][self.shop_id]['items'][self.item_id]
        item['consumable'] = not item['consumable']
        save_shops(shops)
        
        button.style = discord.ButtonStyle.green if item['consumable'] else discord.ButtonStyle.red
        await interaction.response.edit_message(view=self)

class ShopView(discord.ui.View):
    def __init__(self, shop_owner_id: str, shop_id: str, page: int = 0):
        super().__init__(timeout=300)
        self.shop_owner_id = shop_owner_id
        self.shop_id = shop_id
        self.page = page
        self.category_filter = None
    
    @discord.ui.button(label='購買', style=discord.ButtonStyle.green, emoji='🛒')
    async def buy_item(self, interaction: discord.Interaction, button: discord.ui.Button):
        shops = get_shops()
        shop = shops[self.shop_owner_id][self.shop_id]
        items = list(shop['items'].items())
        
        if not items:
            await interaction.response.send_message("❌ 商店目前沒有商品！", ephemeral=True)
            return
        
        # 創建選擇菜單
        options = []
        for item_id, item in items:
            if item['price'] > 0:  # 只顯示非賣品以外的商品
                options.append(
                    discord.SelectOption(
                        label=item['name'],
                        description=f"價格: {item['price']} {shop['currency_emoji']} | {item['category']}",
                        value=item_id
                    )
                )
        
        if not options:
            await interaction.response.send_message("❌ 沒有可購買的商品！", ephemeral=True)
            return
        
        select = discord.ui.Select(placeholder="選擇要購買的商品...", options=options)
        
        async def select_callback(select_interaction: discord.Interaction):
            item_id = select.values[0]
            item = shop['items'][item_id]
            
            # 檢查用戶餘額
            user_id = str(select_interaction.user.id)
            init_user(user_id)
            users = get_users()
            
            if users[user_id]['balance'] < item['price']:
                await select_interaction.response.send_message(
                    f"❌ 餘額不足！需要 {item['price']} {shop['currency_emoji']}，你只有 {users[user_id]['balance']} {shop['currency_emoji']}",
                    ephemeral=True
                )
                return
            
            # 扣款並添加物品
            users[user_id]['balance'] -= item['price']
            if item_id not in users[user_id]['inventory']:
                users[user_id]['inventory'][item_id] = {
                    "name": item['name'],
                    "quantity": 0,
                    "shop_id": self.shop_id,
                    "shop_owner": self.shop_owner_id,
                    "item_data": item.copy()
                }
            users[user_id]['inventory'][item_id]['quantity'] += 1
            save_users(users)
            
            embed = discord.Embed(
                title="✅ 購買成功！",
                description=f"你購買了 **{item['name']}**",
                color=discord.Color.green()
            )
            embed.add_field(name="花費", value=f"{item['price']} {shop['currency_emoji']}", inline=True)
            embed.add_field(name="剩餘餘額", value=f"{users[user_id]['balance']} {shop['currency_emoji']}", inline=True)
            
            await select_interaction.response.send_message(embed=embed, ephemeral=True)
        
        select.callback = select_callback
        view = discord.ui.View()
        view.add_item(select)
        
        await interaction.response.send_message("請選擇要購買的商品：", view=view, ephemeral=True)
    
    @discord.ui.button(label='上一頁', style=discord.ButtonStyle.gray, emoji='◀️')
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
            await self.update_shop_display(interaction)
        else:
            await interaction.response.send_message("已經是第一頁了！", ephemeral=True)
    
    @discord.ui.button(label='下一頁', style=discord.ButtonStyle.gray, emoji='▶️')
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        shops = get_shops()
        shop = shops[self.shop_owner_id][self.shop_id]
        items = list(shop['items'].items())
        
        if (self.page + 1) * 5 < len(items):
            self.page += 1
            await self.update_shop_display(interaction)
        else:
            await interaction.response.send_message("已經是最後一頁了！", ephemeral=True)
    
    async def update_shop_display(self, interaction: discord.Interaction):
        shops = get_shops()
        shop = shops[self.shop_owner_id][self.shop_id]
        
        embed = discord.Embed(
            title=f"🏪 {shop['name']}",
            description=shop['description'],
            color=discord.Color.blue()
        )
        
        if shop['banner_url']:
            embed.set_image(url=shop['banner_url'])
        
        embed.add_field(name="貨幣", value=f"{shop['currency_emoji']} {shop['currency_name']}", inline=True)
        
        items = list(shop['items'].items())
        start_idx = self.page * 5
        end_idx = start_idx + 5
        page_items = items[start_idx:end_idx]
        
        if page_items:
            for item_id, item in page_items:
                price_str = "非賣品" if item['price'] == 0 else f"{item['price']} {shop['currency_emoji']}"
                embed.add_field(
                    name=f"{item['name']} ({item['category']})",
                    value=f"{item['description']}\n價格: {price_str}",
                    inline=False
                )
        else:
            embed.add_field(name="商品列表", value="目前沒有商品", inline=False)
        
        embed.set_footer(text=f"第 {self.page + 1} 頁 | 共 {len(items)} 件商品")
        
        await interaction.response.edit_message(embed=embed, view=self)

# ==================== 背包相關視圖 ====================

class InventoryView(discord.ui.View):
    def __init__(self, user_id: str, page: int = 0, category: str = None):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.page = page
        self.category = category
    
    @discord.ui.button(label='使用物品', style=discord.ButtonStyle.green, emoji='✨')
    async def use_item(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ 這不是你的背包！", ephemeral=True)
            return
        
        users = get_users()
        inventory = users[self.user_id]['inventory']
        
        if not inventory:
            await interaction.response.send_message("❌ 背包是空的！", ephemeral=True)
            return
        
        # 創建選擇菜單
        options = []
        for item_id, item_data in inventory.items():
            if item_data['quantity'] > 0 and item_data['item_data'].get('usable', True):
                options.append(
                    discord.SelectOption(
                        label=item_data['name'],
                        description=f"數量: {item_data['quantity']} | {item_data['item_data']['category']}",
                        value=item_id
                    )
                )
        
        if not options:
            await interaction.response.send_message("❌ 沒有可使用的物品！", ephemeral=True)
            return
        
        select = discord.ui.Select(placeholder="選擇要使用的物品...", options=options)
        
        async def select_callback(select_interaction: discord.Interaction):
            item_id = select.values[0]
            item_data = inventory[item_id]
            
            # 使用物品
            embed = discord.Embed(
                title="✨ 使用物品",
                description=f"你使用了 **{item_data['name']}**",
                color=discord.Color.purple()
            )
            
            use_desc = item_data['item_data'].get('use_description', item_data['item_data']['description'])
            embed.add_field(name="效果", value=use_desc, inline=False)
            
            if item_data['item_data']['image_url']:
                embed.set_thumbnail(url=item_data['item_data']['image_url'])
            
            # 如果是消耗品，減少數量
            if item_data['item_data'].get('consumable', True):
                item_data['quantity'] -= 1
                if item_data['quantity'] <= 0:
                    del users[self.user_id]['inventory'][item_id]
                    embed.set_footer(text="物品已用完")
                else:
                    embed.set_footer(text=f"剩餘數量: {item_data['quantity']}")
            else:
                embed.set_footer(text="物品保留在背包中（可重複使用）")
            
            save_users(users)
            await select_interaction.response.send_message(embed=embed, ephemeral=True)
        
        select.callback = select_callback
        view = discord.ui.View()
        view.add_item(select)
        
        await interaction.response.send_message("請選擇要使用的物品：", view=view, ephemeral=True)
    
    @discord.ui.button(label='切換類別', style=discord.ButtonStyle.blurple, emoji='📁')
    async def change_category(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ 這不是你的背包！", ephemeral=True)
            return
        
        users = get_users()
        inventory = users[self.user_id]['inventory']
        
        # 獲取所有類別
        categories = set()
        for item_data in inventory.values():
            if item_data['quantity'] > 0:
                categories.add(item_data['item_data']['category'])
        
        if not categories:
            await interaction.response.send_message("❌ 背包是空的！", ephemeral=True)
            return
        
        options = [discord.SelectOption(label="全部", value="all", description="顯示所有物品")]
        for cat in sorted(categories):
            options.append(discord.SelectOption(label=cat, value=cat))
        
        select = discord.ui.Select(placeholder="選擇類別...", options=options)
        
        async def select_callback(select_interaction: discord.Interaction):
            selected = select.values[0]
            self.category = None if selected == "all" else selected
            self.page = 0
            await self.update_inventory_display(select_interaction)
        
        select.callback = select_callback
        view = discord.ui.View()
        view.add_item(select)
        
        await interaction.response.send_message("選擇物品類別：", view=view, ephemeral=True)

    async def update_inventory_display(self, interaction: discord.Interaction):
        users = get_users()
        inventory = users[self.user_id]['inventory']
        
        # 過濾類別
        filtered_items = []
        for item_id, item_data in inventory.items():
            if item_data['quantity'] > 0:
                if self.category is None or item_data['item_data']['category'] == self.category:
                    filtered_items.append((item_id, item_data))
        
        embed = discord.Embed(
            title="🎒 我的背包",
            description=f"類別: {self.category or '全部'}",
            color=discord.Color.gold()
        )
        
        # 顯示餘額
        embed.add_field(name="💰 餘額", value=f"{users[self.user_id]['balance']}", inline=False)
        
        if filtered_items:
            start_idx = self.page * 10
            end_idx = start_idx + 10
            page_items = filtered_items[start_idx:end_idx]
            
            for item_id, item_data in page_items:
                consumable_tag = "🔄 可重複使用" if not item_data['item_data'].get('consumable', True) else "💨 消耗品"
                usable_tag = "✅ 可使用" if item_data['item_data'].get('usable', True) else "❌ 不可使用"
                
                embed.add_field(
                    name=f"{item_data['name']} x{item_data['quantity']}",
                    value=f"{item_data['item_data']['category']} | {consumable_tag} | {usable_tag}",
                    inline=False
                )
        else:
            embed.add_field(name="背包", value="空空如也...", inline=False)
        
        embed.set_footer(text=f"第 {self.page + 1} 頁 | 共 {len(filtered_items)} 件物品")
        
        await interaction.response.edit_message(embed=embed, view=self)

# ==================== 角色卡相關 ====================

class CreateCharacterModal(discord.ui.Modal, title='創建角色'):
    char_name = discord.ui.TextInput(
        label='角色名稱',
        placeholder='輸入角色名稱...',
        required=True,
        max_length=50
    )
    
    hp = discord.ui.TextInput(
        label='生命值 (HP)',
        placeholder='例如: 100',
        required=True,
        max_length=10
    )
    
    mp = discord.ui.TextInput(
        label='魔力值 (MP)',
        placeholder='例如: 50',
        required=True,
        max_length=10
    )
    
    attack = discord.ui.TextInput(
        label='攻擊力',
        placeholder='例如: 20',
        required=True,
        max_length=10
    )
    
    defense = discord.ui.TextInput(
        label='防禦力',
        placeholder='例如: 15',
        required=True,
        max_length=10
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            hp = int(self.hp.value)
            mp = int(self.mp.value)
            attack = int(self.attack.value)
            defense = int(self.defense.value)
        except ValueError:
            await interaction.response.send_message("❌ 數值必須是整數！", ephemeral=True)
            return
        
        users = get_users()
        user_id = str(interaction.user.id)
        init_user(user_id)
        
        characters = get_characters()
        char_id = f"char_{user_id}"
        characters[char_id] = {
            "user_id": user_id,
            "name": self.char_name.value,
            "hp": hp,
            "max_hp": hp,
            "mp": mp,
            "max_mp": mp,
            "attack": attack,
            "defense": defense,
            "level": 1,
            "exp": 0,
            "created_at": datetime.now().isoformat()
        }
        
        users[user_id]['character'] = char_id
        save_characters(characters)
        save_users(users)
        
        embed = discord.Embed(
            title="✅ 角色創建成功！",
            description=f"角色 **{self.char_name.value}** 已創建",
            color=discord.Color.green()
        )
        embed.add_field(name="HP", value=f"{hp}/{hp}", inline=True)
        embed.add_field(name="MP", value=f"{mp}/{mp}", inline=True)
        embed.add_field(name="攻擊力", value=attack, inline=True)
        embed.add_field(name="防禦力", value=defense, inline=True)
        embed.add_field(name="等級", value="1", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ==================== 斜線指令 ====================

@bot.tree.command(name="創建商店", description="創建一個新的商店")
async def create_shop(interaction: discord.Interaction):
    await interaction.response.send_modal(CreateShopModal())

@bot.tree.command(name="我的商店", description="查看你的所有商店")
async def my_shops(interaction: discord.Interaction):
    shops = get_shops()
    user_id = str(interaction.user.id)
    
    if user_id not in shops or not shops[user_id]:
        await interaction.response.send_message("❌ 你還沒有創建任何商店！使用 `/創建商店` 來創建一個。", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🏪 我的商店列表",
        color=discord.Color.blue()
    )
    
    for shop_id, shop in shops[user_id].items():
        embed.add_field(
            name=f"{shop['name']} ({shop_id})",
            value=f"貨幣: {shop['currency_emoji']} {shop['currency_name']}\n商品數量: {len(shop['items'])}",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="添加商品", description="向商店添加商品")
@app_commands.describe(商店id="商店的ID（例如: shop_1）")
async def add_item(interaction: discord.Interaction, 商店id: str):
    shops = get_shops()
    user_id = str(interaction.user.id)
    
    if user_id not in shops or 商店id not in shops[user_id]:
        await interaction.response.send_message("❌ 找不到該商店！請使用 `/我的商店` 查看你的商店列表。", ephemeral=True)
        return
    
    await interaction.response.send_modal(AddItemModal(商店id))

@bot.tree.command(name="查看商店", description="查看某個商店")
@app_commands.describe(
    用戶="商店擁有者",
    商店id="商店的ID（例如: shop_1）"
)
async def view_shop(interaction: discord.Interaction, 用戶: discord.User, 商店id: str):
    shops = get_shops()
    owner_id = str(用戶.id)
    
    if owner_id not in shops or 商店id not in shops[owner_id]:
        await interaction.response.send_message("❌ 找不到該商店！", ephemeral=True)
        return
    
    shop = shops[owner_id][商店id]
    
    embed = discord.Embed(
        title=f"🏪 {shop['name']}",
        description=shop['description'],
        color=discord.Color.blue()
    )
    
    if shop['banner_url']:
        embed.set_image(url=shop['banner_url'])
    
    embed.add_field(name="擁有者", value=用戶.mention, inline=True)
    embed.add_field(name="貨幣", value=f"{shop['currency_emoji']} {shop['currency_name']}", inline=True)
    embed.add_field(name="商品數量", value=len(shop['items']), inline=True)
    
    # 顯示商品列表
    if shop['items']:
        for item_id, item in list(shop['items'].items())[:5]:  # 只顯示前5個
            price_str = "非賣品" if item['price'] == 0 else f"{item['price']} {shop['currency_emoji']}"
            embed.add_field(
                name=f"{item['name']} ({item['category']})",
                value=f"{item['description']}\n價格: {price_str}",
                inline=False
            )
    
    view = ShopView(owner_id, 商店id)
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="背包", description="查看你的背包")
async def inventory(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    init_user(user_id)
    users = get_users()
    inventory = users[user_id]['inventory']
    
    embed = discord.Embed(
        title="🎒 我的背包",
        color=discord.Color.gold()
    )
    
    embed.add_field(name="💰 餘額", value=f"{users[user_id]['balance']}", inline=False)
    
    if inventory:
        # 統計各類別物品數量
        categories = {}
        for item_data in inventory.values():
            if item_data['quantity'] > 0:
                cat = item_data['item_data']['category']
                categories[cat] = categories.get(cat, 0) + 1
        
        embed.add_field(
            name="物品統計",
            value="\n".join([f"{cat}: {count}件" for cat, count in categories.items()]),
            inline=False
        )
        
        # 顯示前幾個物品
        shown = 0
        for item_id, item_data in inventory.items():
            if item_data['quantity'] > 0 and shown < 5:
                consumable_tag = "🔄" if not item_data['item_data'].get('consumable', True) else "💨"
                embed.add_field(
                    name=f"{item_data['name']} x{item_data['quantity']}",
                    value=f"{consumable_tag} {item_data['item_data']['category']}",
                    inline=True
                )
                shown += 1
    else:
        embed.add_field(name="背包", value="空空如也...", inline=False)
    
    view = InventoryView(user_id)
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="創建角色", description="創建你的RPG角色")
async def create_character(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    users = get_users()
    
    if user_id in users and users[user_id].get('character'):
        await interaction.response.send_message("❌ 你已經有角色了！使用 `/角色卡` 查看。", ephemeral=True)
        return
    
    await interaction.response.send_modal(CreateCharacterModal())

@bot.tree.command(name="角色卡", description="查看你的角色信息")
async def character_sheet(interaction: discord.Interaction, 用戶: Optional[discord.User] = None):
    target_user = 用戶 or interaction.user
    user_id = str(target_user.id)
    
    users = get_users()
    if user_id not in users or not users[user_id].get('character'):
        await interaction.response.send_message("❌ 該用戶還沒有創建角色！", ephemeral=True)
        return
    
    characters = get_characters()
    char_id = users[user_id]['character']
    char = characters[char_id]
    
    embed = discord.Embed(
        title=f"⚔️ {char['name']}",
        description=f"{target_user.mention} 的角色",
        color=discord.Color.purple()
    )
    
    # HP條
    hp_percent = char['hp'] / char['max_hp']
    hp_bar = "█" * int(hp_percent * 10) + "░" * (10 - int(hp_percent * 10))
    embed.add_field(
        name=f"❤️ HP",
        value=f"{hp_bar} {char['hp']}/{char['max_hp']}",
        inline=False
    )
    
    # MP條
    mp_percent = char['mp'] / char['max_mp']
    mp_bar = "█" * int(mp_percent * 10) + "░" * (10 - int(mp_percent * 10))
    embed.add_field(
        name=f"💙 MP",
        value=f"{mp_bar} {char['mp']}/{char['max_mp']}",
        inline=False
    )
    
    embed.add_field(name="⚔️ 攻擊力", value=char['attack'], inline=True)
    embed.add_field(name="🛡️ 防禦力", value=char['defense'], inline=True)
    embed.add_field(name="⭐ 等級", value=char['level'], inline=True)
    embed.add_field(name="✨ 經驗值", value=f"{char['exp']}/100", inline=True)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="簽到", description="每日簽到獲得獎勵")
async def checkin(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    init_user(user_id)
    
    checkins = get_checkins()
    now = datetime.now()
    today = now.date().isoformat()
    
    # 檢查今天是否已簽到
    if user_id in checkins and checkins[user_id].get('last_checkin') == today:
        await interaction.response.send_message("❌ 你今天已經簽到過了！明天再來吧~", ephemeral=True)
        return
    
    # 獲取收入身份組設定
    income_roles = get_income_roles()
    guild = interaction.guild
    member = guild.get_member(interaction.user.id)
    
    base_reward = 100
    bonus = 0
    bonus_roles = []
    
    # 檢查用戶是否有收入身份組
    for role in member.roles:
        role_id = str(role.id)
        if role_id in income_roles:
            bonus += income_roles[role_id]['daily_income']
            bonus_roles.append(role.name)
    
    total_reward = base_reward + bonus
    
    # 更新用戶餘額
    users = get_users()
    users[user_id]['balance'] += total_reward
    save_users(users)
    
    # 記錄簽到
    if user_id not in checkins:
        checkins[user_id] = {"streak": 0}
    
    # 檢查連續簽到
    last_checkin = checkins[user_id].get('last_checkin')
    if last_checkin:
        last_date = datetime.fromisoformat(last_checkin).date()
        if (now.date() - last_date).days == 1:
            checkins[user_id]['streak'] += 1
        else:
            checkins[user_id]['streak'] = 1
    else:
        checkins[user_id]['streak'] = 1
    
    checkins[user_id]['last_checkin'] = today
    save_checkins(checkins)
    
    embed = discord.Embed(
        title="✅ 簽到成功！",
        description=f"你獲得了 **{total_reward}** 💰",
        color=discord.Color.green()
    )
    
    embed.add_field(name="基礎獎勵", value=f"{base_reward} 💰", inline=True)
    if bonus > 0:
        embed.add_field(name="身份組加成", value=f"+{bonus} 💰", inline=True)
        embed.add_field(name="加成來自", value="\n".join(bonus_roles), inline=False)
    
    embed.add_field(name="連續簽到", value=f"{checkins[user_id]['streak']} 天", inline=True)
    embed.add_field(name="當前餘額", value=f"{users[user_id]['balance']} 💰", inline=True)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="添加收入身份組", description="設置某個身份組的每日收入（管理員）")
@app_commands.describe(
    身份組="要設置的身份組",
    每日收入="每日簽到時獲得的額外收入"
)
@app_commands.checks.has_permissions(administrator=True)
async def add_income_role(interaction: discord.Interaction, 身份組: discord.Role, 每日收入: int):
    income_roles = get_income_roles()
    role_id = str(身份組.id)
    
    income_roles[role_id] = {
        "name": 身份組.name,
        "daily_income": 每日收入
    }
    
    save_income_roles(income_roles)
    
    embed = discord.Embed(
        title="✅ 收入身份組設置成功",
        description=f"身份組 **{身份組.name}** 的每日收入已設置為 **{每日收入}** 💰",
        color=discord.Color.green()
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="收入身份組列表", description="查看所有收入身份組")
async def list_income_roles(interaction: discord.Interaction):
    income_roles = get_income_roles()
    
    if not income_roles:
        await interaction.response.send_message("❌ 目前沒有設置任何收入身份組。", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="💎 收入身份組列表",
        color=discord.Color.blue()
    )
    
    for role_id, role_data in income_roles.items():
        embed.add_field(
            name=role_data['name'],
            value=f"每日收入: {role_data['daily_income']} 💰",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="贈送金幣", description="贈送金幣給其他玩家")
@app_commands.describe(
    用戶="要贈送的對象",
    金額="贈送金額"
)
async def transfer_money(interaction: discord.Interaction, 用戶: discord.User, 金額: int):
    if 金額 <= 0:
        await interaction.response.send_message("❌ 金額必須大於0！", ephemeral=True)
        return
    
    if 用戶.id == interaction.user.id:
        await interaction.response.send_message("❌ 不能贈送給自己！", ephemeral=True)
        return
    
    sender_id = str(interaction.user.id)
    receiver_id = str(用戶.id)
    
    init_user(sender_id)
    init_user(receiver_id)
    
    users = get_users()
    
    if users[sender_id]['balance'] < 金額:
        await interaction.response.send_message(
            f"❌ 餘額不足！你只有 {users[sender_id]['balance']} 💰",
            ephemeral=True
        )
        return
    
    # 轉帳
    users[sender_id]['balance'] -= 金額
    users[receiver_id]['balance'] += 金額
    save_users(users)
    
    embed = discord.Embed(
        title="✅ 轉帳成功",
        description=f"你贈送了 **{金額}** 💰 給 {用戶.mention}",
        color=discord.Color.green()
    )
    embed.add_field(name="你的餘額", value=f"{users[sender_id]['balance']} 💰", inline=True)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="商品設置", description="設置商品的屬性（商店擁有者）")
@app_commands.describe(
    商店id="商店ID",
    商品編號="商品ID（例如: item_1）"
)
async def item_settings(interaction: discord.Interaction, 商店id: str, 商品編號: str):
    shops = get_shops()
    user_id = str(interaction.user.id)
    
    if user_id not in shops or 商店id not in shops[user_id]:
        await interaction.response.send_message("❌ 找不到該商店！", ephemeral=True)
        return
    
    if 商品編號 not in shops[user_id][商店id]['items']:
        await interaction.response.send_message("❌ 找不到該商品！", ephemeral=True)
        return
    
    item = shops[user_id][商店id]['items'][商品編號]
    
    embed = discord.Embed(
        title=f"⚙️ {item['name']} - 設置",
        color=discord.Color.blue()
    )
    embed.add_field(name="可使用", value="✅" if item.get('usable', True) else "❌", inline=True)
    embed.add_field(name="可轉售", value="✅" if item.get('resellable', True) else "❌", inline=True)
    embed.add_field(name="消耗型", value="✅" if item.get('consumable', True) else "❌", inline=True)
    
    view = ItemSettingsView(商店id, 商品編號, user_id)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="修改使用描述", description="修改物品使用時的描述")
@app_commands.describe(
    商店id="商店ID",
    商品編號="商品ID",
    使用描述="使用物品時顯示的描述"
)
async def set_use_description(interaction: discord.Interaction, 商店id: str, 商品編號: str, 使用描述: str):
    shops = get_shops()
    user_id = str(interaction.user.id)
    
    if user_id not in shops or 商店id not in shops[user_id]:
        await interaction.response.send_message("❌ 找不到該商店！", ephemeral=True)
        return
    
    if 商品編號 not in shops[user_id][商店id]['items']:
        await interaction.response.send_message("❌ 找不到該商品！", ephemeral=True)
        return
    
    shops[user_id][商店id]['items'][商品編號]['use_description'] = 使用描述
    save_shops(shops)
    
    await interaction.response.send_message(
        f"✅ 已更新 **{shops[user_id][商店id]['items'][商品編號]['name']}** 的使用描述！",
        ephemeral=True
    )

@bot.tree.command(name="幫助", description="顯示所有可用指令")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📚 指令列表",
        description="這個機器人的所有功能",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="🏪 商店系統",
        value="""
        `/創建商店` - 創建新商店
        `/我的商店` - 查看你的商店
        `/添加商品` - 添加商品到商店
        `/查看商店` - 查看某個商店
        `/商品設置` - 設置商品屬性
        `/修改使用描述` - 修改物品使用描述
        """,
        inline=False
    )
    
    embed.add_field(
        name="🎒 背包系統",
        value="""
        `/背包` - 查看你的背包
        可在背包中使用物品、切換類別查看
        """,
        inline=False
    )
    
    embed.add_field(
        name="⚔️ 角色系統",
        value="""
        `/創建角色` - 創建RPG角色
        `/角色卡` - 查看角色信息
        """,
        inline=False
    )
    
    embed.add_field(
        name="💰 經濟系統",
        value="""
        `/簽到` - 每日簽到獲得金幣
        `/贈送金幣` - 贈送金幣給其他玩家
        `/添加收入身份組` - 設置身份組收入（管理員）
        `/收入身份組列表` - 查看收入身份組
        """,
        inline=False
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ==================== 事件處理 ====================

@bot.event
async def on_ready():
    print(f'✅ 機器人已登入為 {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f'✅ 同步了 {len(synced)} 個斜線指令')
    except Exception as e:
        print(f'❌ 同步指令時出錯: {e}')

# ==================== 啟動機器人 ====================

if __name__ == "__main__":
    TOKEN = os.getenv('DISCORD_TOKEN')
    if not TOKEN:
        print("❌ 錯誤: 請設置 DISCORD_TOKEN 環境變數")
    else:
        bot.run(TOKEN)