import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List

try:
    import discord
    from discord.ext import commands
    from discord import app_commands
except ImportError:
    print("❌ 錯誤: discord.py 未安裝")
    print("請執行: pip install discord.py")
    exit(1)

# 初始化機器人
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# 數據文件路徑
DATA_DIR = "data"
GUILDS_FILE = f"{DATA_DIR}/guilds.json"
SHOPS_FILE = f"{DATA_DIR}/shops.json"
USERS_FILE = f"{DATA_DIR}/users.json"
CHARACTERS_FILE = f"{DATA_DIR}/characters.json"
CHECKIN_FILE = f"{DATA_DIR}/checkins.json"

# 確保數據目錄存在
os.makedirs(DATA_DIR, exist_ok=True)

# ==================== 管理員檢查函數 ====================

def is_bot_admin(guild_id: str, user_id: str) -> bool:
    """檢查用戶是否為機器人管理員"""
    guilds = load_json(GUILDS_FILE, {})
    if guild_id not in guilds:
        return False
    bot_admins = guilds[guild_id].get('bot_admins', [])
    return str(user_id) in bot_admins

def add_bot_admin(guild_id: str, user_id: str):
    """添加機器人管理員"""
    guilds = load_json(GUILDS_FILE, {})
    if guild_id not in guilds:
        guilds[guild_id] = {'currencies': {}, 'income_roles': {}, 'bot_admins': []}
    if 'bot_admins' not in guilds[guild_id]:
        guilds[guild_id]['bot_admins'] = []
    if str(user_id) not in guilds[guild_id]['bot_admins']:
        guilds[guild_id]['bot_admins'].append(str(user_id))
    save_json(GUILDS_FILE, guilds)

def remove_bot_admin(guild_id: str, user_id: str):
    """移除機器人管理員"""
    guilds = load_json(GUILDS_FILE, {})
    if guild_id in guilds and 'bot_admins' in guilds[guild_id]:
        if str(user_id) in guilds[guild_id]['bot_admins']:
            guilds[guild_id]['bot_admins'].remove(str(user_id))
            save_json(GUILDS_FILE, guilds)

async def check_admin_permission(interaction: discord.Interaction) -> bool:
    """檢查用戶是否有管理員權限（Discord管理員或機器人管理員）"""
    # 檢查Discord管理員權限
    if interaction.user.guild_permissions.administrator:
        return True
    # 檢查機器人自定義管理員
    guild_id = str(interaction.guild.id)
    user_id = str(interaction.user.id)
    return is_bot_admin(guild_id, user_id)

def admin_only():
    """裝飾器：只允許管理員使用"""
    async def predicate(interaction: discord.Interaction) -> bool:
        if await check_admin_permission(interaction):
            return True
        await interaction.response.send_message(
            "❌ 此指令僅限管理員使用！\n💡 需要Discord管理員權限或被設為機器人管理員。",
            ephemeral=True
        )
        return False
    return app_commands.check(predicate)

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

def get_guilds():
    """獲取所有伺服器數據"""
    return load_json(GUILDS_FILE, {})

def save_guilds(guilds):
    """保存伺服器數據"""
    save_json(GUILDS_FILE, guilds)

def init_guild(guild_id: str):
    """初始化伺服器數據"""
    guilds = get_guilds()
    if guild_id not in guilds:
        guilds[guild_id] = {
            "currencies": {},  # 貨幣列表
            "income_roles": {}  # 收入身份組
        }
        save_guilds(guilds)
    return guilds[guild_id]

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

def init_user(user_id: str, guild_id: str):
    """初始化用戶數據"""
    users = get_users()
    user_key = f"{guild_id}_{user_id}"
    
    if user_key not in users:
        users[user_key] = {
            "user_id": user_id,
            "guild_id": guild_id,
            "balances": {},  # 各種貨幣的餘額
            "inventory": {},
            "character": None
        }
        save_users(users)
    return users[user_key]

def get_user_key(guild_id: str, user_id: str) -> str:
    """獲取用戶的唯一鍵"""
    return f"{guild_id}_{user_id}"

# ==================== 貨幣管理Modal ====================

class CreateCurrencyModal(discord.ui.Modal, title='創建貨幣'):
    currency_id = discord.ui.TextInput(
        label='貨幣ID',
        placeholder='例如: gold, diamond, coin（英文，不可重複）',
        required=True,
        max_length=20
    )
    
    currency_name = discord.ui.TextInput(
        label='貨幣名稱',
        placeholder='例如: 金幣、鑽石、元寶',
        required=True,
        max_length=20
    )
    
    currency_emoji = discord.ui.TextInput(
        label='貨幣表情符號',
        placeholder='例如: 💰 或 💎',
        required=False,
        max_length=50
    )
    
    description = discord.ui.TextInput(
        label='貨幣描述',
        placeholder='簡短描述這個貨幣的用途...',
        required=False,
        style=discord.TextStyle.long,
        max_length=200
    )

    async def on_submit(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        guilds = get_guilds()
        init_guild(guild_id)
        
        currency_id = self.currency_id.value.lower().strip()
        
        # 檢查ID是否已存在
        if currency_id in guilds[guild_id]['currencies']:
            await interaction.response.send_message(
                f"❌ 貨幣ID `{currency_id}` 已存在！請使用其他ID。",
                ephemeral=True
            )
            return
        
        # 檢查ID格式（只允許英文和數字）
        if not currency_id.replace('_', '').isalnum() or not currency_id[0].isalpha():
            await interaction.response.send_message(
                "❌ 貨幣ID只能包含英文字母、數字和下劃線，且必須以字母開頭！",
                ephemeral=True
            )
            return
        
        guilds[guild_id]['currencies'][currency_id] = {
            "name": self.currency_name.value,
            "emoji": self.currency_emoji.value or "💰",
            "description": self.description.value or "一種貨幣",
            "created_at": datetime.now().isoformat()
        }
        
        save_guilds(guilds)
        
        embed = discord.Embed(
            title="✅ 貨幣創建成功！",
            description=f"貨幣 **{self.currency_name.value}** 已創建",
            color=discord.Color.green()
        )
        embed.add_field(name="貨幣ID", value=f"`{currency_id}`", inline=True)
        embed.add_field(name="符號", value=self.currency_emoji.value or "💰", inline=True)
        
        await interaction.response.send_message(embed=embed)

# ==================== 商店相關Modal ====================

class CreateShopModal(discord.ui.Modal, title='創建商店'):
    shop_id = discord.ui.TextInput(
        label='商店ID',
        placeholder='自定義ID，例如: magic_shop, weapon_store',
        required=True,
        max_length=30
    )
    
    shop_name = discord.ui.TextInput(
        label='商店名稱',
        placeholder='輸入你的商店名稱...',
        required=True,
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
    
    def __init__(self, guild_id: str):
        super().__init__()
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction):
        shops = get_shops()
        user_id = str(interaction.user.id)
        shop_key = f"{self.guild_id}_{user_id}"
        
        if shop_key not in shops:
            shops[shop_key] = {}
        
        shop_id = self.shop_id.value.lower().strip()
        
        # 檢查商店ID是否已存在
        if shop_id in shops[shop_key]:
            await interaction.response.send_message(
                f"❌ 你已經有一個ID為 `{shop_id}` 的商店了！請使用其他ID。",
                ephemeral=True
            )
            return
        
        # 檢查ID格式
        if not shop_id.replace('_', '').isalnum() or not shop_id[0].isalpha():
            await interaction.response.send_message(
                "❌ 商店ID只能包含英文字母、數字和下劃線，且必須以字母開頭！",
                ephemeral=True
            )
            return
        
        shops[shop_key][shop_id] = {
            "name": self.shop_name.value,
            "shop_id": shop_id,
            "owner": user_id,
            "guild_id": self.guild_id,
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
        embed.add_field(name="商店ID", value=f"`{shop_id}`", inline=False)
        embed.add_field(name="使用方法", value=f"使用 `/添加商品 {shop_id}` 來添加商品", inline=False)
        
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
    
    # ✅ 新增：庫存數量輸入
    stock = discord.ui.TextInput(
        label='庫存數量',
        placeholder='輸入庫存數量（-1表示無限庫存）',
        required=True,
        max_length=10,
        default="-1"
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
    
    def __init__(self, shop_key: str, shop_id: str, currency_id: str, currency_data: dict):
        super().__init__()
        self.shop_key = shop_key
        self.shop_id = shop_id
        self.currency_id = currency_id
        self.currency_data = currency_data
        # 移除 image_url 從 Modal，改為之後詢問

    async def on_submit(self, interaction: discord.Interaction):
        try:
            price = int(self.price.value)
            if price < 0:
                raise ValueError
        except ValueError:
            await interaction.response.send_message("❌ 價格必須是非負整數！", ephemeral=True)
            return
        
        # ✅ 新增：驗證庫存數量
        try:
            stock = int(self.stock.value)
            if stock < -1:
                raise ValueError
        except ValueError:
            await interaction.response.send_message("❌ 庫存數量必須是大於等於-1的整數！（-1表示無限庫存）", ephemeral=True)
            return
        
        shops = get_shops()
        
        if self.shop_key not in shops or self.shop_id not in shops[self.shop_key]:
            await interaction.response.send_message("❌ 找不到該商店！", ephemeral=True)
            return
        
        item_id = f"item_{len(shops[self.shop_key][self.shop_id]['items']) + 1}"
        shops[self.shop_key][self.shop_id]['items'][item_id] = {
            "name": self.item_name.value,
            "price": price,
            "currency_id": self.currency_id,
            "category": self.category.value,
            "description": self.description.value,
            "image_url": None,  # 稍後可以單獨設置
            "stock": stock,  # ✅ 新增：庫存數量
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
        
        price_display = "非賣品" if price == 0 else f"{price} {self.currency_data['emoji']} {self.currency_data['name']}"
        stock_display = "無限" if stock == -1 else f"{stock} 個"
        
        embed.add_field(name="價格", value=price_display, inline=True)
        embed.add_field(name="庫存", value=stock_display, inline=True)  # ✅ 新增：顯示庫存
        embed.add_field(name="類別", value=self.category.value, inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ==================== 選擇貨幣View ====================

class CurrencySelectView(discord.ui.View):
    def __init__(self, guild_id: str, user_id: str, shop_id: str, action: str):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        self.user_id = user_id
        self.shop_id = shop_id
        self.action = action
        self.selected_currency = None
        
        # 添加貨幣選擇菜單
        guilds = get_guilds()
        if guild_id in guilds and guilds[guild_id]['currencies']:
            options = []
            for curr_id, curr_data in guilds[guild_id]['currencies'].items():
                options.append(
                    discord.SelectOption(
                        label=curr_data['name'],
                        description=curr_data.get('description', '')[:100],
                        value=curr_id,
                        emoji=curr_data['emoji']
                    )
                )
            
            select = discord.ui.Select(
                placeholder="選擇貨幣類型...",
                options=options,
                custom_id="currency_select"
            )
            select.callback = self.currency_selected
            self.add_item(select)
    
    async def currency_selected(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ 這不是你的操作！", ephemeral=True)
            return
        
        currency_id = interaction.data['values'][0]
        guilds = get_guilds()
        currency_data = guilds[self.guild_id]['currencies'][currency_id]
        
        if self.action == "add_item":
            # 打開添加商品的Modal
            shop_key = f"{self.guild_id}_{self.user_id}"
            modal = AddItemModal(shop_key, self.shop_id, currency_id, currency_data)
            await interaction.response.send_modal(modal)

# ==================== 購買數量選擇Modal ==================== 
# ✅ 新增：購買數量輸入Modal
class PurchaseQuantityModal(discord.ui.Modal, title='選擇購買數量'):
    quantity = discord.ui.TextInput(
        label='購買數量',
        placeholder='輸入要購買的數量',
        required=True,
        max_length=10,
        default="1"
    )
    
    def __init__(self, shop_key: str, shop_id: str, item_id: str, guild_id: str):
        super().__init__()
        self.shop_key = shop_key
        self.shop_id = shop_id
        self.item_id = item_id
        self.guild_id = guild_id
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            quantity = int(self.quantity.value)
            if quantity <= 0:
                raise ValueError
        except ValueError:
            await interaction.response.send_message("❌ 數量必須是正整數！", ephemeral=True)
            return
        
        shops = get_shops()
        shop = shops[self.shop_key][self.shop_id]
        item = shop['items'][self.item_id]
        guilds = get_guilds()
        currency_data = guilds[self.guild_id]['currencies'][item['currency_id']]
        
        # ✅ 檢查庫存
        if item['stock'] != -1:  # 不是無限庫存
            if item['stock'] < quantity:
                await interaction.response.send_message(
                    f"❌ 庫存不足！目前只剩 {item['stock']} 個",
                    ephemeral=True
                )
                return
        
        # 計算總價
        total_price = item['price'] * quantity
        
        # 檢查用戶餘額
        user_id = str(interaction.user.id)
        user_key = get_user_key(self.guild_id, user_id)
        init_user(user_id, self.guild_id)
        users = get_users()
        
        user_balance = users[user_key]['balances'].get(item['currency_id'], 0)
        
        if user_balance < total_price:
            await interaction.response.send_message(
                f"❌ {currency_data['name']}不足！需要 {total_price} {currency_data['emoji']}，你只有 {user_balance} {currency_data['emoji']}",
                ephemeral=True
            )
            return
        
        # ✅ 扣除庫存
        if item['stock'] != -1:
            item['stock'] -= quantity
        
        # 扣款並添加物品
        users[user_key]['balances'][item['currency_id']] = user_balance - total_price
        
        if self.item_id not in users[user_key]['inventory']:
            users[user_key]['inventory'][self.item_id] = {
                "name": item['name'],
                "quantity": 0,
                "shop_id": self.shop_id,
                "shop_key": self.shop_key,
                "item_data": item.copy()
            }
        users[user_key]['inventory'][self.item_id]['quantity'] += quantity
        
        save_shops(shops)
        save_users(users)
        
        embed = discord.Embed(
            title="✅ 購買成功！",
            description=f"你購買了 **{item['name']} x{quantity}**",
            color=discord.Color.green()
        )
        embed.add_field(
            name="花費",
            value=f"{total_price} {currency_data['emoji']} {currency_data['name']}",
            inline=True
        )
        embed.add_field(
            name="剩餘餘額",
            value=f"{users[user_key]['balances'][item['currency_id']]} {currency_data['emoji']}",
            inline=True
        )
        
        # ✅ 顯示剩餘庫存
        if item['stock'] != -1:
            embed.add_field(
                name="商品剩餘庫存",
                value=f"{item['stock']} 個",
                inline=True
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ==================== 商店和背包View ====================

class ItemSettingsView(discord.ui.View):
    def __init__(self, shop_key: str, shop_id: str, item_id: str, owner_id: str):
        super().__init__(timeout=300)
        self.shop_key = shop_key
        self.shop_id = shop_id
        self.item_id = item_id
        self.owner_id = owner_id
    
    @discord.ui.button(label='可使用', style=discord.ButtonStyle.gray, custom_id='toggle_usable')
    async def toggle_usable(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.owner_id:
            await interaction.response.send_message("❌ 只有商店擁有者可以修改設定！", ephemeral=True)
            return
        
        shops = get_shops()
        item = shops[self.shop_key][self.shop_id]['items'][self.item_id]
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
        item = shops[self.shop_key][self.shop_id]['items'][self.item_id]
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
        item = shops[self.shop_key][self.shop_id]['items'][self.item_id]
        item['consumable'] = not item['consumable']
        save_shops(shops)
        
        button.style = discord.ButtonStyle.green if item['consumable'] else discord.ButtonStyle.red
        await interaction.response.edit_message(view=self)

class ShopView(discord.ui.View):
    def __init__(self, shop_key: str, shop_id: str, guild_id: str, page: int = 0):
        super().__init__(timeout=300)
        self.shop_key = shop_key
        self.shop_id = shop_id
        self.guild_id = guild_id
        self.page = page
    
    @discord.ui.button(label='購買', style=discord.ButtonStyle.green, emoji='🛒')
    async def buy_item(self, interaction: discord.Interaction, button: discord.ui.Button):
        shops = get_shops()
        shop = shops[self.shop_key][self.shop_id]
        items = list(shop['items'].items())
        
        if not items:
            await interaction.response.send_message("❌ 商店目前沒有商品！", ephemeral=True)
            return
        
        # 創建選擇菜單
        guilds = get_guilds()
        options = []
        for item_id, item in items:
            # ✅ 修改：檢查庫存和價格
            if item['price'] > 0:  # 只顯示非賣品以外的商品
                # ✅ 檢查是否有庫存
                if item.get('stock', -1) == 0:
                    continue  # 跳過無庫存商品
                
                currency_data = guilds[self.guild_id]['currencies'][item['currency_id']]
                price_display = f"{item['price']} {currency_data['emoji']}"
                
                # ✅ 顯示庫存信息
                stock_display = "無限" if item.get('stock', -1) == -1 else f"剩{item['stock']}"
                
                options.append(
                    discord.SelectOption(
                        label=item['name'],
                        description=f"價格: {price_display} | {item['category']} | 庫存: {stock_display}",
                        value=item_id
                    )
                )
        
        if not options:
            await interaction.response.send_message("❌ 沒有可購買的商品或所有商品都已售罄！", ephemeral=True)
            return
        
        select = discord.ui.Select(placeholder="選擇要購買的商品...", options=options[:25])  # Discord限制25個選項
        
        async def select_callback(select_interaction: discord.Interaction):
            item_id = select.values[0]
            # ✅ 修改：打開購買數量Modal
            modal = PurchaseQuantityModal(self.shop_key, self.shop_id, item_id, self.guild_id)
            await select_interaction.response.send_modal(modal)
        
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
        shop = shops[self.shop_key][self.shop_id]
        items = list(shop['items'].items())
        
        if (self.page + 1) * 5 < len(items):
            self.page += 1
            await self.update_shop_display(interaction)
        else:
            await interaction.response.send_message("已經是最後一頁了！", ephemeral=True)
    
    async def update_shop_display(self, interaction: discord.Interaction):
        shops = get_shops()
        shop = shops[self.shop_key][self.shop_id]
        guilds = get_guilds()
        
        embed = discord.Embed(
            title=f"🏪 {shop['name']}",
            description=shop['description'],
            color=discord.Color.blue()
        )
        
        if shop['banner_url']:
            embed.set_image(url=shop['banner_url'])
        
        items = list(shop['items'].items())
        start_idx = self.page * 5
        end_idx = start_idx + 5
        page_items = items[start_idx:end_idx]
        
        if page_items:
            for item_id, item in page_items:
                currency_data = guilds[self.guild_id]['currencies'][item['currency_id']]
                price_str = "非賣品" if item['price'] == 0 else f"{item['price']} {currency_data['emoji']} {currency_data['name']}"
                
                # ✅ 新增：顯示庫存信息
                stock = item.get('stock', -1)
                if stock == -1:
                    stock_str = "📦 庫存: 無限"
                elif stock == 0:
                    stock_str = "❌ 已售罄"
                else:
                    stock_str = f"📦 庫存: {stock}"
                
                embed.add_field(
                    name=f"{item['name']} ({item['category']})",
                    value=f"{item['description']}\n💰 價格: {price_str}\n{stock_str}",
                    inline=False
                )
        else:
            embed.add_field(name="商品列表", value="目前沒有商品", inline=False)
        
        embed.set_footer(text=f"第 {self.page + 1} 頁 | 共 {len(items)} 件商品")
        
        await interaction.response.edit_message(embed=embed, view=self)

class InventoryView(discord.ui.View):
    def __init__(self, user_key: str, guild_id: str, page: int = 0, category: str = None):
        super().__init__(timeout=300)
        self.user_key = user_key
        self.guild_id = guild_id
        self.page = page
        self.category = category
    
    @discord.ui.button(label='使用物品', style=discord.ButtonStyle.green, emoji='✨')
    async def use_item(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 從user_key提取user_id
        user_id = self.user_key.split('_', 1)[1]
        if str(interaction.user.id) != user_id:
            await interaction.response.send_message("❌ 這不是你的背包！", ephemeral=True)
            return
        
        users = get_users()
        inventory = users[self.user_key]['inventory']
        
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
        
        select = discord.ui.Select(placeholder="選擇要使用的物品...", options=options[:25])  # Discord限制25個選項
        
        async def select_callback(select_interaction: discord.Interaction):
            item_id = select.values[0]
            item_data = inventory[item_id]
            
            # 使用物品
            embed = discord.Embed(
                title="✨ 使用物品",
                description=f"你使用了 **{item_data['name']}**",
                color=discord.Color.purple()
            )
            
            use_desc = item_data['item_data'].get('use_description') or item_data['item_data']['description']
            embed.add_field(name="效果", value=use_desc, inline=False)
            
            if item_data['item_data'].get('image_url'):
                embed.set_thumbnail(url=item_data['item_data']['image_url'])
            
            # 如果是消耗品，減少數量
            if item_data['item_data'].get('consumable', True):
                item_data['quantity'] -= 1
                if item_data['quantity'] <= 0:
                    del users[self.user_key]['inventory'][item_id]
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
        user_id = self.user_key.split('_', 1)[1]
        if str(interaction.user.id) != user_id:
            await interaction.response.send_message("❌ 這不是你的背包！", ephemeral=True)
            return
        
        users = get_users()
        inventory = users[self.user_key]['inventory']
        
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
        
        select = discord.ui.Select(placeholder="選擇類別...", options=options[:25])
        
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
        inventory = users[self.user_key]['inventory']
        guilds = get_guilds()
        
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
        
        # 顯示所有貨幣餘額
        balances_text = []
        for curr_id, balance in users[self.user_key]['balances'].items():
            if curr_id in guilds[self.guild_id]['currencies']:
                curr_data = guilds[self.guild_id]['currencies'][curr_id]
                balances_text.append(f"{curr_data['emoji']} {curr_data['name']}: {balance}")
        
        if balances_text:
            embed.add_field(name="💰 餘額", value="\n".join(balances_text), inline=False)
        
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

# ==================== 角色卡Modal ====================

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
    
    def __init__(self, guild_id: str):
        super().__init__()
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction):
        try:
            hp = int(self.hp.value)
            mp = int(self.mp.value)
            attack = int(self.attack.value)
            defense = int(self.defense.value)
        except ValueError:
            await interaction.response.send_message("❌ 數值必須是整數！", ephemeral=True)
            return
        
        user_id = str(interaction.user.id)
        user_key = get_user_key(self.guild_id, user_id)
        init_user(user_id, self.guild_id)
        
        users = get_users()
        characters = get_characters()
        char_id = f"char_{user_key}"
        
        characters[char_id] = {
            "user_id": user_id,
            "guild_id": self.guild_id,
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
        
        users[user_key]['character'] = char_id
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

# ========== 貨幣管理指令 ==========

@bot.tree.command(name="創建貨幣", description="創建一種新的貨幣（管理員）")
async def create_currency(interaction: discord.Interaction):
    # 檢查管理員權限
    if not await check_admin_permission(interaction):
        await interaction.response.send_message(
            "❌ 此指令僅限管理員使用！",
            ephemeral=True
        )
        return
    
    await interaction.response.send_modal(CreateCurrencyModal())

@bot.tree.command(name="貨幣列表", description="查看伺服器的所有貨幣")
async def list_currencies(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)
    guilds = get_guilds()
    init_guild(guild_id)
    
    if not guilds[guild_id]['currencies']:
        await interaction.response.send_message(
            "❌ 伺服器還沒有創建任何貨幣！\n管理員可以使用 `/創建貨幣` 來創建。",
            ephemeral=True
        )
        return
    
    embed = discord.Embed(
        title="💎 貨幣列表",
        description=f"{interaction.guild.name} 的所有貨幣",
        color=discord.Color.gold()
    )
    
    for curr_id, curr_data in guilds[guild_id]['currencies'].items():
        embed.add_field(
            name=f"{curr_data['emoji']} {curr_data['name']} (`{curr_id}`)",
            value=curr_data.get('description', '沒有描述'),
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="刪除貨幣", description="刪除一種貨幣（管理員，謹慎使用！）")
@app_commands.describe(貨幣id="要刪除的貨幣ID")
async def delete_currency(interaction: discord.Interaction, 貨幣id: str):
    # 檢查管理員權限
    if not await check_admin_permission(interaction):
        await interaction.response.send_message(
            "❌ 此指令僅限管理員使用！",
            ephemeral=True
        )
        return
    
    guild_id = str(interaction.guild.id)
    guilds = get_guilds()
    init_guild(guild_id)
    
    currency_id = 貨幣id.lower().strip()
    
    if currency_id not in guilds[guild_id]['currencies']:
        await interaction.response.send_message(f"❌ 找不到貨幣ID `{currency_id}`！", ephemeral=True)
        return
    
    currency_name = guilds[guild_id]['currencies'][currency_id]['name']
    del guilds[guild_id]['currencies'][currency_id]
    save_guilds(guilds)
    
    await interaction.response.send_message(
        f"✅ 已刪除貨幣 **{currency_name}** (`{currency_id}`)\n⚠️ 注意：已有的商品和餘額仍然保留此貨幣的記錄",
        ephemeral=True
    )

# ========== 商店管理指令 ==========

@bot.tree.command(name="創建商店", description="創建一個新的商店")
async def create_shop(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)
    guilds = get_guilds()
    init_guild(guild_id)
    
    # 檢查是否有貨幣
    if not guilds[guild_id]['currencies']:
        await interaction.response.send_message(
            "❌ 伺服器還沒有任何貨幣！\n請先請管理員使用 `/創建貨幣` 創建貨幣。",
            ephemeral=True
        )
        return
    
    await interaction.response.send_modal(CreateShopModal(guild_id))

@bot.tree.command(name="我的商店", description="查看你的所有商店")
async def my_shops(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)
    user_id = str(interaction.user.id)
    shop_key = f"{guild_id}_{user_id}"
    
    shops = get_shops()
    
    if shop_key not in shops or not shops[shop_key]:
        await interaction.response.send_message(
            "❌ 你還沒有創建任何商店！使用 `/創建商店` 來創建一個。",
            ephemeral=True
        )
        return
    
    embed = discord.Embed(
        title="🏪 我的商店列表",
        color=discord.Color.blue()
    )
    
    for shop_id, shop in shops[shop_key].items():
        embed.add_field(
            name=f"{shop['name']} (`{shop_id}`)",
            value=f"商品數量: {len(shop['items'])}",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="添加商品", description="向商店添加商品")
@app_commands.describe(商店id="商店的ID")
async def add_item(interaction: discord.Interaction, 商店id: str):
    guild_id = str(interaction.guild.id)
    user_id = str(interaction.user.id)
    shop_key = f"{guild_id}_{user_id}"
    shops = get_shops()
    
    shop_id = 商店id.lower().strip()
    
    if shop_key not in shops or shop_id not in shops[shop_key]:
        await interaction.response.send_message(
            f"❌ 找不到ID為 `{shop_id}` 的商店！請使用 `/我的商店` 查看你的商店列表。",
            ephemeral=True
        )
        return
    
    # 顯示貨幣選擇界面
    view = CurrencySelectView(guild_id, user_id, shop_id, "add_item")
    await interaction.response.send_message("請選擇商品使用的貨幣類型：", view=view, ephemeral=True)

@bot.tree.command(name="查看商店", description="查看某個商店")
@app_commands.describe(
    用戶="商店擁有者",
    商店id="商店的ID"
)
async def view_shop(interaction: discord.Interaction, 用戶: discord.User, 商店id: str):
    guild_id = str(interaction.guild.id)
    owner_id = str(用戶.id)
    shop_key = f"{guild_id}_{owner_id}"
    shops = get_shops()
    
    shop_id = 商店id.lower().strip()
    
    if shop_key not in shops or shop_id not in shops[shop_key]:
        await interaction.response.send_message(f"❌ 找不到該商店！", ephemeral=True)
        return
    
    shop = shops[shop_key][shop_id]
    
    embed = discord.Embed(
        title=f"🏪 {shop['name']}",
        description=shop['description'],
        color=discord.Color.blue()
    )
    
    if shop.get('banner_url'):
        embed.set_image(url=shop['banner_url'])
    
    embed.add_field(name="擁有者", value=用戶.mention, inline=True)
    embed.add_field(name="商店ID", value=f"`{shop_id}`", inline=True)
    embed.add_field(name="商品數量", value=len(shop['items']), inline=True)
    
    # 顯示商品列表
    guilds = get_guilds()
    if shop['items']:
        for item_id, item in list(shop['items'].items())[:5]:  # 只顯示前5個
            currency_data = guilds[guild_id]['currencies'][item['currency_id']]
            price_str = "非賣品" if item['price'] == 0 else f"{item['price']} {currency_data['emoji']} {currency_data['name']}"
            
            # ✅ 新增：顯示庫存
            stock = item.get('stock', -1)
            if stock == -1:
                stock_str = "📦 無限庫存"
            elif stock == 0:
                stock_str = "❌ 已售罄"
            else:
                stock_str = f"📦 剩餘: {stock}"
            
            embed.add_field(
                name=f"{item['name']} ({item['category']})",
                value=f"{item['description']}\n💰 {price_str}\n{stock_str}",
                inline=False
            )
    
    view = ShopView(shop_key, shop_id, guild_id)
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="刪除商店", description="刪除你的商店")
@app_commands.describe(商店id="要刪除的商店ID")
async def delete_shop(interaction: discord.Interaction, 商店id: str):
    guild_id = str(interaction.guild.id)
    user_id = str(interaction.user.id)
    shop_key = f"{guild_id}_{user_id}"
    shops = get_shops()
    
    shop_id = 商店id.lower().strip()
    
    if shop_key not in shops or shop_id not in shops[shop_key]:
        await interaction.response.send_message(f"❌ 找不到ID為 `{shop_id}` 的商店！", ephemeral=True)
        return
    
    shop_name = shops[shop_key][shop_id]['name']
    del shops[shop_key][shop_id]
    
    if not shops[shop_key]:  # 如果沒有商店了，刪除整個key
        del shops[shop_key]
    
    save_shops(shops)
    
    await interaction.response.send_message(
        f"✅ 已刪除商店 **{shop_name}** (`{shop_id}`)",
        ephemeral=True
    )

# ✅ 新增：補貨指令
@bot.tree.command(name="補貨", description="為商品補充庫存")
@app_commands.describe(
    商店id="商店的ID",
    商品編號="商品ID（例如: item_1）",
    數量="補充的數量"
)
async def restock(interaction: discord.Interaction, 商店id: str, 商品編號: str, 數量: int):
    guild_id = str(interaction.guild.id)
    user_id = str(interaction.user.id)
    shop_key = f"{guild_id}_{user_id}"
    shops = get_shops()
    
    shop_id = 商店id.lower().strip()
    
    if shop_key not in shops or shop_id not in shops[shop_key]:
        await interaction.response.send_message("❌ 找不到該商店！", ephemeral=True)
        return
    
    if 商品編號 not in shops[shop_key][shop_id]['items']:
        await interaction.response.send_message("❌ 找不到該商品！", ephemeral=True)
        return
    
    if 數量 <= 0:
        await interaction.response.send_message("❌ 數量必須大於0！", ephemeral=True)
        return
    
    item = shops[shop_key][shop_id]['items'][商品編號]
    
    if item.get('stock', -1) == -1:
        await interaction.response.send_message("❌ 此商品為無限庫存，無需補貨！", ephemeral=True)
        return
    
    old_stock = item['stock']
    item['stock'] += 數量
    save_shops(shops)
    
    embed = discord.Embed(
        title="✅ 補貨成功",
        description=f"**{item['name']}** 已補充庫存",
        color=discord.Color.green()
    )
    embed.add_field(name="補貨前", value=f"{old_stock} 個", inline=True)
    embed.add_field(name="補貨後", value=f"{item['stock']} 個", inline=True)
    embed.add_field(name="補充數量", value=f"+{數量}", inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ========== 背包和角色指令 ==========

@bot.tree.command(name="背包", description="查看你的背包")
async def inventory(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)
    user_id = str(interaction.user.id)
    user_key = get_user_key(guild_id, user_id)
    init_user(user_id, guild_id)
    
    users = get_users()
    inventory = users[user_key]['inventory']
    guilds = get_guilds()
    
    embed = discord.Embed(
        title="🎒 我的背包",
        color=discord.Color.gold()
    )
    
    # 顯示所有貨幣餘額
    balances_text = []
    for curr_id, balance in users[user_key]['balances'].items():
        if curr_id in guilds[guild_id]['currencies']:
            curr_data = guilds[guild_id]['currencies'][curr_id]
            balances_text.append(f"{curr_data['emoji']} {curr_data['name']}: {balance}")
    
    if balances_text:
        embed.add_field(name="💰 餘額", value="\n".join(balances_text), inline=False)
    else:
        embed.add_field(name="💰 餘額", value="暫無貨幣", inline=False)
    
    if inventory:
        # 統計各類別物品數量
        categories = {}
        for item_data in inventory.values():
            if item_data['quantity'] > 0:
                cat = item_data['item_data']['category']
                categories[cat] = categories.get(cat, 0) + 1
        
        if categories:
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
    
    view = InventoryView(user_key, guild_id)
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="創建角色", description="創建你的RPG角色")
async def create_character(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)
    user_id = str(interaction.user.id)
    user_key = get_user_key(guild_id, user_id)
    
    users = get_users()
    
    if user_key in users and users[user_key].get('character'):
        await interaction.response.send_message("❌ 你已經有角色了！使用 `/角色卡` 查看。", ephemeral=True)
        return
    
    await interaction.response.send_modal(CreateCharacterModal(guild_id))

@bot.tree.command(name="角色卡", description="查看角色信息")
@app_commands.describe(用戶="要查看的用戶（不填則查看自己）")
async def character_sheet(interaction: discord.Interaction, 用戶: Optional[discord.User] = None):
    guild_id = str(interaction.guild.id)
    target_user = 用戶 or interaction.user
    user_id = str(target_user.id)
    user_key = get_user_key(guild_id, user_id)
    
    users = get_users()
    if user_key not in users or not users[user_key].get('character'):
        await interaction.response.send_message("❌ 該用戶還沒有創建角色！", ephemeral=True)
        return
    
    characters = get_characters()
    char_id = users[user_key]['character']
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

# ========== 簽到和收入指令 ==========

@bot.tree.command(name="簽到", description="每日簽到獲得獎勵")
@app_commands.describe(貨幣id="要獲得的貨幣類型（不填則使用默認貨幣）")
async def checkin(interaction: discord.Interaction, 貨幣id: Optional[str] = None):
    guild_id = str(interaction.guild.id)
    user_id = str(interaction.user.id)
    user_key = get_user_key(guild_id, user_id)
    init_user(user_id, guild_id)
    
    guilds = get_guilds()
    init_guild(guild_id)
    
    # 確定使用的貨幣
    if 貨幣id:
        currency_id = 貨幣id.lower().strip()
        if currency_id not in guilds[guild_id]['currencies']:
            await interaction.response.send_message(f"❌ 找不到貨幣ID `{currency_id}`！", ephemeral=True)
            return
    else:
        # 使用第一個可用的貨幣
        if not guilds[guild_id]['currencies']:
            await interaction.response.send_message(
                "❌ 伺服器還沒有任何貨幣！請聯繫管理員。",
                ephemeral=True
            )
            return
        currency_id = list(guilds[guild_id]['currencies'].keys())[0]
    
    currency_data = guilds[guild_id]['currencies'][currency_id]
    
    checkins = get_checkins()
    now = datetime.now()
    today = now.date().isoformat()
    checkin_key = f"{user_key}_{currency_id}"
    
    # 檢查今天是否已簽到
    if checkin_key in checkins and checkins[checkin_key].get('last_checkin') == today:
        await interaction.response.send_message(
            f"❌ 你今天已經簽到過 {currency_data['emoji']} {currency_data['name']} 了！明天再來吧~",
            ephemeral=True
        )
        return
    
    # 獲取收入身份組設定
    income_roles = guilds[guild_id].get('income_roles', {})
    guild = interaction.guild
    member = guild.get_member(interaction.user.id)
    
    base_reward = 100
    bonus = 0
    bonus_roles = []
    
    # 檢查用戶是否有收入身份組（針對此貨幣）
    for role in member.roles:
        role_id = str(role.id)
        if role_id in income_roles:
            role_currencies = income_roles[role_id].get('currencies', {})
            if currency_id in role_currencies:
                bonus += role_currencies[currency_id]
                bonus_roles.append(f"{role.name} (+{role_currencies[currency_id]})")
    
    total_reward = base_reward + bonus
    
    # 更新用戶餘額
    users = get_users()
    if currency_id not in users[user_key]['balances']:
        users[user_key]['balances'][currency_id] = 0
    users[user_key]['balances'][currency_id] += total_reward
    save_users(users)
    
    # 記錄簽到
    if checkin_key not in checkins:
        checkins[checkin_key] = {"streak": 0}
    
    # 檢查連續簽到
    last_checkin = checkins[checkin_key].get('last_checkin')
    if last_checkin:
        last_date = datetime.fromisoformat(last_checkin).date()
        if (now.date() - last_date).days == 1:
            checkins[checkin_key]['streak'] += 1
        else:
            checkins[checkin_key]['streak'] = 1
    else:
        checkins[checkin_key]['streak'] = 1
    
    checkins[checkin_key]['last_checkin'] = today
    save_checkins(checkins)
    
    embed = discord.Embed(
        title="✅ 簽到成功！",
        description=f"你獲得了 **{total_reward}** {currency_data['emoji']} {currency_data['name']}",
        color=discord.Color.green()
    )
    
    embed.add_field(name="基礎獎勵", value=f"{base_reward} {currency_data['emoji']}", inline=True)
    if bonus > 0:
        embed.add_field(name="身份組加成", value=f"+{bonus} {currency_data['emoji']}", inline=True)
        embed.add_field(name="加成來自", value="\n".join(bonus_roles), inline=False)
    
    embed.add_field(name="連續簽到", value=f"{checkins[checkin_key]['streak']} 天", inline=True)
    embed.add_field(
        name="當前餘額",
        value=f"{users[user_key]['balances'][currency_id]} {currency_data['emoji']}",
        inline=True
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="設置簽到收入", description="設置身份組的簽到收入（管理員）")
@app_commands.describe(
    身份組="要設置的身份組",
    貨幣id="貨幣類型",
    每日收入="每日簽到時獲得的額外收入"
)
async def set_income_role(interaction: discord.Interaction, 身份組: discord.Role, 貨幣id: str, 每日收入: int):
    # 檢查管理員權限
    if not await check_admin_permission(interaction):
        await interaction.response.send_message(
            "❌ 此指令僅限管理員使用！",
            ephemeral=True
        )
        return
    
    guild_id = str(interaction.guild.id)
    guilds = get_guilds()
    init_guild(guild_id)
    
    currency_id = 貨幣id.lower().strip()
    
    if currency_id not in guilds[guild_id]['currencies']:
        await interaction.response.send_message(f"❌ 找不到貨幣ID `{currency_id}`！", ephemeral=True)
        return
    
    currency_data = guilds[guild_id]['currencies'][currency_id]
    role_id = str(身份組.id)
    
    if 'income_roles' not in guilds[guild_id]:
        guilds[guild_id]['income_roles'] = {}
    
    if role_id not in guilds[guild_id]['income_roles']:
        guilds[guild_id]['income_roles'][role_id] = {
            "name": 身份組.name,
            "currencies": {}
        }
    
    guilds[guild_id]['income_roles'][role_id]['currencies'][currency_id] = 每日收入
    guilds[guild_id]['income_roles'][role_id]['name'] = 身份組.name  # 更新名稱
    
    save_guilds(guilds)
    
    embed = discord.Embed(
        title="✅ 收入身份組設置成功",
        description=f"身份組 **{身份組.name}** 的 {currency_data['emoji']} {currency_data['name']} 每日收入已設置為 **{每日收入}**",
        color=discord.Color.green()
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="收入身份組列表", description="查看所有收入身份組")
async def list_income_roles(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)
    guilds = get_guilds()
    init_guild(guild_id)
    
    income_roles = guilds[guild_id].get('income_roles', {})
    
    if not income_roles:
        await interaction.response.send_message("❌ 目前沒有設置任何收入身份組。", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="💎 收入身份組列表",
        color=discord.Color.blue()
    )
    
    for role_id, role_data in income_roles.items():
        currencies_text = []
        for curr_id, income in role_data.get('currencies', {}).items():
            if curr_id in guilds[guild_id]['currencies']:
                curr_data = guilds[guild_id]['currencies'][curr_id]
                currencies_text.append(f"{curr_data['emoji']} {curr_data['name']}: +{income}")
        
        if currencies_text:
            embed.add_field(
                name=role_data['name'],
                value="\n".join(currencies_text),
                inline=False
            )
    
    await interaction.response.send_message(embed=embed)

# ========== 管理員金錢管理指令 ==========

@bot.tree.command(name="添加金錢", description="給玩家添加金錢（管理員）")
@app_commands.describe(
    用戶="要添加金錢的玩家",
    貨幣id="貨幣類型",
    金額="要添加的金額"
)
async def add_money(interaction: discord.Interaction, 用戶: discord.User, 貨幣id: str, 金額: int):
    # 檢查管理員權限
    if not await check_admin_permission(interaction):
        await interaction.response.send_message(
            "❌ 此指令僅限管理員使用！",
            ephemeral=True
        )
        return
    
    guild_id = str(interaction.guild.id)
    guilds = get_guilds()
    init_guild(guild_id)
    
    currency_id = 貨幣id.lower().strip()
    
    if currency_id not in guilds[guild_id]['currencies']:
        await interaction.response.send_message(f"❌ 找不到貨幣ID `{currency_id}`！", ephemeral=True)
        return
    
    if 金額 <= 0:
        await interaction.response.send_message("❌ 金額必須大於0！", ephemeral=True)
        return
    
    currency_data = guilds[guild_id]['currencies'][currency_id]
    user_id = str(用戶.id)
    user_key = get_user_key(guild_id, user_id)
    init_user(user_id, guild_id)
    
    users = get_users()
    if currency_id not in users[user_key]['balances']:
        users[user_key]['balances'][currency_id] = 0
    users[user_key]['balances'][currency_id] += 金額
    save_users(users)
    
    embed = discord.Embed(
        title="✅ 添加金錢成功",
        description=f"已為 {用戶.mention} 添加 **{金額}** {currency_data['emoji']} {currency_data['name']}",
        color=discord.Color.green()
    )
    embed.add_field(
        name="當前餘額",
        value=f"{users[user_key]['balances'][currency_id]} {currency_data['emoji']}",
        inline=True
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="移除金錢", description="移除玩家的金錢（管理員）")
@app_commands.describe(
    用戶="要移除金錢的玩家",
    貨幣id="貨幣類型",
    金額="要移除的金額"
)
async def remove_money(interaction: discord.Interaction, 用戶: discord.User, 貨幣id: str, 金額: int):
    # 檢查管理員權限
    if not await check_admin_permission(interaction):
        await interaction.response.send_message(
            "❌ 此指令僅限管理員使用！",
            ephemeral=True
        )
        return
    
    guild_id = str(interaction.guild.id)
    guilds = get_guilds()
    init_guild(guild_id)
    
    currency_id = 貨幣id.lower().strip()
    
    if currency_id not in guilds[guild_id]['currencies']:
        await interaction.response.send_message(f"❌ 找不到貨幣ID `{currency_id}`！", ephemeral=True)
        return
    
    if 金額 <= 0:
        await interaction.response.send_message("❌ 金額必須大於0！", ephemeral=True)
        return
    
    currency_data = guilds[guild_id]['currencies'][currency_id]
    user_id = str(用戶.id)
    user_key = get_user_key(guild_id, user_id)
    init_user(user_id, guild_id)
    
    users = get_users()
    if currency_id not in users[user_key]['balances']:
        users[user_key]['balances'][currency_id] = 0
    
    old_balance = users[user_key]['balances'][currency_id]
    users[user_key]['balances'][currency_id] = max(0, old_balance - 金額)
    save_users(users)
    
    actual_removed = old_balance - users[user_key]['balances'][currency_id]
    
    embed = discord.Embed(
        title="✅ 移除金錢成功",
        description=f"已從 {用戶.mention} 移除 **{actual_removed}** {currency_data['emoji']} {currency_data['name']}",
        color=discord.Color.orange()
    )
    
    if actual_removed < 金額:
        embed.add_field(
            name="⚠️ 注意",
            value=f"用戶餘額不足，實際移除 {actual_removed}，餘額已歸零",
            inline=False
        )
    
    embed.add_field(
        name="當前餘額",
        value=f"{users[user_key]['balances'][currency_id]} {currency_data['emoji']}",
        inline=True
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="查看餘額", description="查看玩家的餘額（管理員）")
@app_commands.describe(用戶="要查看的玩家")
async def check_balance(interaction: discord.Interaction, 用戶: discord.User):
    # 檢查管理員權限
    if not await check_admin_permission(interaction):
        await interaction.response.send_message(
            "❌ 此指令僅限管理員使用！",
            ephemeral=True
        )
        return
    
    guild_id = str(interaction.guild.id)
    user_id = str(用戶.id)
    user_key = get_user_key(guild_id, user_id)
    init_user(user_id, guild_id)
    
    users = get_users()
    guilds = get_guilds()
    
    embed = discord.Embed(
        title=f"💰 {用戶.display_name} 的餘額",
        color=discord.Color.gold()
    )
    
    balances_text = []
    for curr_id, balance in users[user_key]['balances'].items():
        if curr_id in guilds[guild_id]['currencies']:
            curr_data = guilds[guild_id]['currencies'][curr_id]
            balances_text.append(f"{curr_data['emoji']} {curr_data['name']}: **{balance}**")
    
    if balances_text:
        embed.description = "\n".join(balances_text)
    else:
        embed.description = "該用戶暫無任何貨幣"
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ========== 其他指令 ==========

@bot.tree.command(name="贈送金幣", description="贈送金幣給其他玩家")
@app_commands.describe(
    用戶="要贈送的對象",
    貨幣id="貨幣類型",
    金額="贈送金額"
)
async def transfer_money(interaction: discord.Interaction, 用戶: discord.User, 貨幣id: str, 金額: int):
    guild_id = str(interaction.guild.id)
    guilds = get_guilds()
    init_guild(guild_id)
    
    currency_id = 貨幣id.lower().strip()
    
    if currency_id not in guilds[guild_id]['currencies']:
        await interaction.response.send_message(f"❌ 找不到貨幣ID `{currency_id}`！", ephemeral=True)
        return
    
    if 金額 <= 0:
        await interaction.response.send_message("❌ 金額必須大於0！", ephemeral=True)
        return
    
    if 用戶.id == interaction.user.id:
        await interaction.response.send_message("❌ 不能贈送給自己！", ephemeral=True)
        return
    
    currency_data = guilds[guild_id]['currencies'][currency_id]
    sender_id = str(interaction.user.id)
    receiver_id = str(用戶.id)
    
    sender_key = get_user_key(guild_id, sender_id)
    receiver_key = get_user_key(guild_id, receiver_id)
    
    init_user(sender_id, guild_id)
    init_user(receiver_id, guild_id)
    
    users = get_users()
    
    sender_balance = users[sender_key]['balances'].get(currency_id, 0)
    
    if sender_balance < 金額:
        await interaction.response.send_message(
            f"❌ {currency_data['name']}不足！你只有 {sender_balance} {currency_data['emoji']}",
            ephemeral=True
        )
        return
    
    # 轉帳
    users[sender_key]['balances'][currency_id] = sender_balance - 金額
    
    if currency_id not in users[receiver_key]['balances']:
        users[receiver_key]['balances'][currency_id] = 0
    users[receiver_key]['balances'][currency_id] += 金額
    
    save_users(users)
    
    embed = discord.Embed(
        title="✅ 轉帳成功",
        description=f"你贈送了 **{金額}** {currency_data['emoji']} {currency_data['name']} 給 {用戶.mention}",
        color=discord.Color.green()
    )
    embed.add_field(
        name="你的餘額",
        value=f"{users[sender_key]['balances'][currency_id]} {currency_data['emoji']}",
        inline=True
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="商品設置", description="設置商品的屬性（商店擁有者）")
@app_commands.describe(
    商店id="商店ID",
    商品編號="商品ID（例如: item_1）"
)
async def item_settings(interaction: discord.Interaction, 商店id: str, 商品編號: str):
    guild_id = str(interaction.guild.id)
    user_id = str(interaction.user.id)
    shop_key = f"{guild_id}_{user_id}"
    shops = get_shops()
    
    shop_id = 商店id.lower().strip()
    
    if shop_key not in shops or shop_id not in shops[shop_key]:
        await interaction.response.send_message("❌ 找不到該商店！", ephemeral=True)
        return
    
    if 商品編號 not in shops[shop_key][shop_id]['items']:
        await interaction.response.send_message("❌ 找不到該商品！", ephemeral=True)
        return
    
    item = shops[shop_key][shop_id]['items'][商品編號]
    
    embed = discord.Embed(
        title=f"⚙️ {item['name']} - 設置",
        color=discord.Color.blue()
    )
    embed.add_field(name="可使用", value="✅" if item.get('usable', True) else "❌", inline=True)
    embed.add_field(name="可轉售", value="✅" if item.get('resellable', True) else "❌", inline=True)
    embed.add_field(name="消耗型", value="✅" if item.get('consumable', True) else "❌", inline=True)
    
    # ✅ 新增：顯示庫存信息
    stock = item.get('stock', -1)
    stock_display = "無限" if stock == -1 else f"{stock} 個"
    embed.add_field(name="📦 庫存", value=stock_display, inline=True)
    
    view = ItemSettingsView(shop_key, shop_id, 商品編號, user_id)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="修改使用描述", description="修改物品使用時的描述")
@app_commands.describe(
    商店id="商店ID",
    商品編號="商品ID",
    使用描述="使用物品時顯示的描述"
)
async def set_use_description(interaction: discord.Interaction, 商店id: str, 商品編號: str, 使用描述: str):
    guild_id = str(interaction.guild.id)
    user_id = str(interaction.user.id)
    shop_key = f"{guild_id}_{user_id}"
    shops = get_shops()
    
    shop_id = 商店id.lower().strip()
    
    if shop_key not in shops or shop_id not in shops[shop_key]:
        await interaction.response.send_message("❌ 找不到該商店！", ephemeral=True)
        return
    
    if 商品編號 not in shops[shop_key][shop_id]['items']:
        await interaction.response.send_message("❌ 找不到該商品！", ephemeral=True)
        return
    
    shops[shop_key][shop_id]['items'][商品編號]['use_description'] = 使用描述
    save_shops(shops)
    
    await interaction.response.send_message(
        f"✅ 已更新 **{shops[shop_key][shop_id]['items'][商品編號]['name']}** 的使用描述！",
        ephemeral=True
    )

# ========== 機器人管理員管理指令 ==========

@bot.tree.command(name="添加管理員", description="添加機器人管理員（需要Discord管理員權限）")
@app_commands.describe(用戶="要設為管理員的用戶")
@app_commands.checks.has_permissions(administrator=True)
async def add_admin(interaction: discord.Interaction, 用戶: discord.User):
    guild_id = str(interaction.guild.id)
    user_id = str(用戶.id)
    
    add_bot_admin(guild_id, user_id)
    
    embed = discord.Embed(
        title="✅ 管理員添加成功",
        description=f"{用戶.mention} 現在是機器人管理員",
        color=discord.Color.green()
    )
    embed.add_field(
        name="權限",
        value="可以使用所有管理員指令（創建貨幣、添加金錢等）",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="移除管理員", description="移除機器人管理員（需要Discord管理員權限）")
@app_commands.describe(用戶="要移除管理員權限的用戶")
@app_commands.checks.has_permissions(administrator=True)
async def remove_admin(interaction: discord.Interaction, 用戶: discord.User):
    guild_id = str(interaction.guild.id)
    user_id = str(用戶.id)
    
    remove_bot_admin(guild_id, user_id)
    
    embed = discord.Embed(
        title="✅ 管理員移除成功",
        description=f"{用戶.mention} 的管理員權限已被移除",
        color=discord.Color.orange()
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="管理員列表", description="查看所有機器人管理員")
async def list_admins(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)
    guilds = load_json(GUILDS_FILE, {})
    
    if guild_id not in guilds or 'bot_admins' not in guilds[guild_id] or not guilds[guild_id]['bot_admins']:
        await interaction.response.send_message(
            "❌ 目前沒有設置任何機器人管理員。\n💡 Discord管理員可以使用 `/添加管理員` 來設置。",
            ephemeral=True
        )
        return
    
    embed = discord.Embed(
        title="👑 機器人管理員列表",
        description="這些用戶可以使用管理員指令",
        color=discord.Color.gold()
    )
    
    admin_mentions = []
    for admin_id in guilds[guild_id]['bot_admins']:
        user = interaction.guild.get_member(int(admin_id))
        if user:
            admin_mentions.append(f"• {user.mention} ({user.name})")
        else:
            admin_mentions.append(f"• <@{admin_id}> (已離開伺服器)")
    
    embed.add_field(
        name="管理員",
        value="\n".join(admin_mentions) if admin_mentions else "無",
        inline=False
    )
    
    embed.set_footer(text="💡 Discord管理員始終擁有所有權限")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="幫助", description="顯示所有可用指令")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📚 指令列表",
        description="這個機器人的所有功能",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="💎 貨幣系統（管理員）",
        value="""
        `/創建貨幣` - 創建新貨幣
        `/貨幣列表` - 查看所有貨幣
        `/刪除貨幣` - 刪除貨幣
        """,
        inline=False
    )
    
    embed.add_field(
        name="🏪 商店系統",
        value="""
        `/創建商店` - 創建新商店（可自定義ID）
        `/我的商店` - 查看你的商店
        `/添加商品` - 添加商品到商店（可設定庫存）
        `/查看商店` - 查看某個商店
        `/刪除商店` - 刪除你的商店
        `/補貨` - 為商品補充庫存 ✨新
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
        `/簽到` - 每日簽到獲得金幣（可指定貨幣）
        `/贈送金幣` - 贈送金幣給其他玩家
        `/設置簽到收入` - 設置身份組收入（管理員）
        `/收入身份組列表` - 查看收入身份組
        `/添加金錢` - 給玩家添加金錢（管理員）
        `/移除金錢` - 移除玩家金錢（管理員）
        `/查看餘額` - 查看玩家餘額（管理員）
        """,
        inline=False
    )
    
    embed.add_field(
        name="👑 管理員管理",
        value="""
        `/添加管理員` - 設置機器人管理員（需Discord管理員）
        `/移除管理員` - 移除機器人管理員（需Discord管理員）
        `/管理員列表` - 查看所有機器人管理員
        """,
        inline=False
    )
    
    embed.set_footer(text="✨ 新增功能：商品庫存系統 | 💡 Discord管理員始終擁有所有管理權限")
    
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