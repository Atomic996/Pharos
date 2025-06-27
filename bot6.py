from web3 import Web3
from eth_utils import to_hex
from eth_abi.abi import encode
from eth_account import Account
from eth_account.messages import encode_defunct
from aiohttp import ClientResponseError, ClientSession, ClientTimeout
# from aiohttp_socks import ProxyConnector # تم تعطيل هذا السطر
from fake_useragent import FakeUserAgent
from datetime import datetime
from colorama import *
import asyncio, random, secrets, json, time, os, pytz

wib = pytz.timezone('Asia/Jakarta')

class PharosTestnet:
    def __init__(self) -> None:
        self.headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "Origin": "https://testnet.pharosnetwork.xyz",
            "Referer": "https://testnet.pharosnetwork.xyz/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": FakeUserAgent().random
        }
        self.BASE_API = "https://api.pharosnetwork.xyz"
        self.RPC_URL = "https://testnet.dplabs-internal.com"
        self.WPHRS_CONTRACT_ADDRESS = "0x76aaaDA469D23216bE5f7C596fA25F282Ff9b364"
        self.CONTRACT_ABI = [
            {
                "inputs": [
                    {"internalType": "address", "name": "user", "type": "address"},
                    {"internalType": "uint256", "name": "amount", "type": "uint256"},
                ],
                "name": "claim",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function",
            },
            {
                "inputs": [
                    {"internalType": "address", "name": "user", "type": "address"}
                ],
                "name": "lastClaim",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function",
            },
        ]
        self.w3 = Web3(Web3.HTTPProvider(self.RPC_URL))
        self.contract = self.w3.eth.contract(
            address=self.WPHRS_CONTRACT_ADDRESS, abi=self.CONTRACT_ABI
        )

    def log(self, text, type=None):
        if type == "error":
            print(
                f"{Fore.CYAN+Style.BRIGHT}[ {datetime.now().astimezone(wib).strftime('%x %X %Z')} ]{Style.RESET_ALL}"
                f"{Fore.WHITE+Style.BRIGHT} | {Style.RESET_ALL}"
                f"{Fore.RED+Style.BRIGHT}{text}{Style.RESET_ALL}"
            )
        else:
            print(
                f"{Fore.CYAN+Style.BRIGHT}[ {datetime.now().astimezone(wib).strftime('%x %X %Z')} ]{Style.RESET_ALL}"
                f"{Fore.WHITE+Style.BRIGHT} | {Style.RESET_ALL}"
                f"{Fore.GREEN+Style.BRIGHT}{text}{Style.RESET_ALL}"
            )

    def format_seconds(self, seconds):
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
        elif minutes > 0:
            return f"{int(minutes)}m {int(seconds)}s"
        else:
            return f"{int(seconds)}s"

    async def get_session(self, proxy=None):
        # تم إزالة أي استخدام لـ ProxyConnector هنا
        # connector = ProxyConnector.from_url(f'socks5://{proxy}') if proxy else None
        # session = ClientSession(connector=connector, timeout=ClientTimeout(total=60))
        session = ClientSession(timeout=ClientTimeout(total=60)) # استخدام جلسة بدون بروكسي
        return session

    async def get_address_info(self, address):
        self.headers["User-Agent"] = FakeUserAgent().random
        async with await self.get_session() as session:
            try:
                response = await session.get(
                    f"{self.BASE_API}/address_info?address={address}",
                    headers=self.headers,
                )
                response.raise_for_status()
                data = await response.json()
                return data
            except ClientResponseError as e:
                if e.status == 429:
                    self.log(
                        f"{Fore.YELLOW}Too Many Requests. Retrying after 5 seconds...{Style.RESET_ALL}",
                        type="error",
                    )
                    await asyncio.sleep(5)
                    return await self.get_address_info(address)
                else:
                    self.log(
                        f"{Fore.RED+Style.BRIGHT}Error fetching address info: {e}{Style.RESET_ALL}",
                        type="error",
                    )
                    return None
            except Exception as e:
                self.log(
                    f"{Fore.RED+Style.BRIGHT}Error fetching address info: {e}{Style.RESET_ALL}",
                    type="error",
                )
                return None

    async def claim_faucet(self, private_key, proxy=None):
        account = Account.from_key(private_key)
        self.headers["User-Agent"] = FakeUserAgent().random
        async with await self.get_session(proxy) as session: # تم تمرير proxy هنا ولكن get_session لا يستخدمه
            try:
                response = await session.post(
                    f"{self.BASE_API}/claim_faucet",
                    headers=self.headers,
                    json={"address": account.address},
                )
                response.raise_for_status()
                data = await response.json()
                return data
            except ClientResponseError as e:
                if e.status == 429:
                    self.log(
                        f"{Fore.YELLOW}Too Many Requests for claim faucet. Retrying after 5 seconds...{Style.RESET_ALL}",
                        type="error",
                    )
                    await asyncio.sleep(5)
                    return await self.claim_faucet(private_key, proxy)
                else:
                    self.log(
                        f"{Fore.RED+Style.BRIGHT}Error claiming faucet: {e}{Style.RESET_ALL}",
                        type="error",
                    )
                    return None
            except Exception as e:
                self.log(
                    f"{Fore.RED+Style.BRIGHT}Error claiming faucet: {e}{Style.RESET_ALL}",
                    type="error",
                )
                return None

    async def get_signature(self, private_key, user_id):
        account = Account.from_key(private_key)
        try:
            signature_message = {
                "types": {
                    "EIP712Domain": [
                        {"name": "name", "type": "string"},
                        {"name": "version", "type": "string"},
                        {"name": "chainId", "type": "uint256"},
                        {"name": "verifyingContract", "type": "address"},
                    ],
                    "SignedMessage": [
                        {"name": "userId", "type": "uint256"},
                        {"name": "wallet", "type": "address"},
                    ],
                },
                "domain": {
                    "name": "Pharos Network Testnet",
                    "version": "1",
                    "chainId": 97,
                    "verifyingContract": "0x4b789139f4007817b1A142e03290075dD47700B0",
                },
                "primaryType": "SignedMessage",
                "message": {"userId": user_id, "wallet": account.address},
            }
            signed_message = Account.sign_typed_data(
                private_key=private_key, full_message=signature_message
            )
            return signed_message.signature.hex()
        except Exception as e:
            self.log(
                f"{Fore.RED+Style.BRIGHT}Error signing message: {e}{Style.RESET_ALL}",
                type="error",
            )
            return None

    async def bind_telegram(self, private_key, user_id, proxy=None):
        signature = await self.get_signature(private_key, user_id)
        if not signature:
            return None
        account = Account.from_key(private_key)
        self.headers["User-Agent"] = FakeUserAgent().random
        async with await self.get_session(proxy) as session: # تم تمرير proxy هنا ولكن get_session لا يستخدمه
            try:
                response = await session.post(
                    f"{self.BASE_API}/bind_telegram",
                    headers=self.headers,
                    json={
                        "address": account.address,
                        "userId": user_id,
                        "signature": signature,
                    },
                )
                response.raise_for_status()
                data = await response.json()
                return data
            except ClientResponseError as e:
                if e.status == 429:
                    self.log(
                        f"{Fore.YELLOW}Too Many Requests for bind telegram. Retrying after 5 seconds...{Style.RESET_ALL}",
                        type="error",
                    )
                    await asyncio.sleep(5)
                    return await self.bind_telegram(private_key, user_id, proxy)
                else:
                    self.log(
                        f"{Fore.RED+Style.BRIGHT}Error binding telegram: {e}{Style.RESET_ALL}",
                        type="error",
                    )
                    return None
            except Exception as e:
                self.log(
                    f"{Fore.RED+Style.BRIGHT}Error binding telegram: {e}{Style.RESET_ALL}",
                    type="error",
                )
                return None

    async def get_token_balance(self, address):
        try:
            checksum_address = Web3.to_checksum_address(self.WPHRS_CONTRACT_ADDRESS)
            balance_wei = self.contract.functions.balanceOf(address).call()
            balance_ether = self.w3.from_wei(balance_wei, "ether")
            return balance_ether
        except Exception as e:
            self.log(
                f"{Fore.RED+Style.BRIGHT}Error getting token balance: {e}{Style.RESET_ALL}",
                type="error",
            )
            return 0

    async def main(self):
        try:
            with open("accounts.txt", "r") as f:
                accounts = f.read().splitlines()

            # Randomize proxies only if proxies are provided
            # if os.path.exists("proxies.txt"):
            #     with open("proxies.txt", "r") as f:
            #         proxies = f.read().splitlines()
            #     random.shuffle(proxies)
            # else:
            #     proxies = [None] * len(accounts) # لا يوجد بروكسيات
            
            # تم حذف جزء البروكسي بالكامل هنا
            
            self.log(
                f"{Fore.YELLOW+Style.BRIGHT}Loaded {len(accounts)} Accounts.{Style.RESET_ALL}"
            )

            for i, account_data in enumerate(accounts):
                # if proxies[i] is not None:
                #     self.log(f"{Fore.MAGENTA+Style.BRIGHT}Using Proxy: {proxies[i]}{Style.RESET_ALL}")

                parts = account_data.split("|")
                private_key = parts[0]
                telegram_user_id = parts[1] if len(parts) > 1 else None

                account = Account.from_key(private_key)
                address = account.address

                self.log(
                    f"{Fore.BLUE+Style.BRIGHT}[ Account {i+1}/{len(accounts)} ]{Style.RESET_ALL}"
                    f"{Fore.WHITE+Style.BRIGHT} | {Style.RESET_ALL}"
                    f"{Fore.CYAN+Style.BRIGHT}Address: {address}{Style.RESET_ALL}"
                )

                address_info = await self.get_address_info(address)
                if address_info:
                    self.log(
                        f"{Fore.GREEN+Style.BRIGHT}Balance: {address_info.get('balance', 'N/A')} PHRS{Style.RESET_ALL}"
                        f"{Fore.WHITE+Style.BRIGHT} | {Style.RESET_ALL}"
                        f"{Fore.GREEN+Style.BRIGHT}Claim Status: {address_info.get('claim_status', 'N/A')}{Style.RESET_ALL}"
                        f"{Fore.WHITE+Style.BRIGHT} | {Style.RESET_ALL}"
                        f"{Fore.GREEN+Style.BRIGHT}Bind Status: {address_info.get('bind_status', 'N/A')}{Style.RESET_ALL}"
                    )

                    if address_info.get("claim_status") == "false":
                        self.log(
                            f"{Fore.YELLOW}Attempting to claim faucet for {address}...{Style.RESET_ALL}"
                        )
                        claim_result = await self.claim_faucet(private_key) # لا يوجد بروكسي هنا
                        if claim_result and claim_result.get("code") == 200:
                            self.log(
                                f"{Fore.GREEN}Faucet claimed successfully for {address}{Style.RESET_ALL}"
                            )
                        else:
                            self.log(
                                f"{Fore.RED}Failed to claim faucet for {address}: {claim_result.get('message', 'Unknown error')}{Style.RESET_ALL}",
                                type="error",
                            )
                    else:
                        self.log(
                            f"{Fore.GREEN}Faucet already claimed for {address}{Style.RESET_ALL}"
                        )

                    if (
                        address_info.get("bind_status") == "false"
                        and telegram_user_id is not None
                    ):
                        self.log(
                            f"{Fore.YELLOW}Attempting to bind Telegram for {address} with User ID {telegram_user_id}...{Style.RESET_ALL}"
                        )
                        bind_result = await self.bind_telegram(
                            private_key, int(telegram_user_id)
                        ) # لا يوجد بروكسي هنا
                        if bind_result and bind_result.get("code") == 200:
                            self.log(
                                f"{Fore.GREEN}Telegram bound successfully for {address}{Style.RESET_ALL}"
                            )
                        else:
                            self.log(
                                f"{Fore.RED}Failed to bind Telegram for {address}: {bind_result.get('message', 'Unknown error')}{Style.RESET_ALL}",
                                type="error",
                            )
                    elif telegram_user_id is None:
                        self.log(
                            f"{Fore.YELLOW}No Telegram User ID provided for {address}. Skipping Telegram binding.{Style.RESET_ALL}"
                        )
                    else:
                        self.log(
                            f"{Fore.GREEN}Telegram already bound for {address}{Style.RESET_ALL}"
                        )

                    token_balance = await self.get_token_balance(address)
                    self.log(
                        f"{Fore.MAGENTA+Style.BRIGHT}WPHRS Token Balance: {token_balance} WPHRS{Style.RESET_ALL}"
                    )
                else:
                    self.log(
                        f"{Fore.RED}Could not retrieve address info for {address}. Skipping...{Style.RESET_ALL}",
                        type="error",
                    )
                self.log(f"{Fore.WHITE+Style.BRIGHT}="*72)
                seconds = 24 * 60 * 60
                while seconds > 0:
                    formatted_time = self.format_seconds(seconds)
                    print(
                        f"{Fore.CYAN+Style.BRIGHT}[ Wait for{Style.RESET_ALL}"
                        f"{Fore.WHITE+Style.BRIGHT} {formatted_time} {Style.RESET_ALL}"
                        f"{Fore.CYAN+Style.BRIGHT}... ]{Style.RESET_ALL}"
                        f"{Fore.WHITE+Style.BRIGHT} | {Style.RESET_ALL}"
                        f"{Fore.BLUE+Style.BRIGHT}All Accounts Have Been Processed.{Style.RESET_ALL}",
                        end="\r"
                    )
                    await asyncio.sleep(1)
                    seconds -= 1

        except FileNotFoundError:
            self.log(f"{Fore.RED}File 'accounts.txt' Not Found.{Style.RESET_ALL}")
            return
        except Exception as e:
            self.log(f"{Fore.RED+Style.BRIGHT}Error: {e}{Style.RESET_ALL}")
            raise e

if __name__ == "__main__":
    try:
        bot = PharosTestnet()
        asyncio.run(bot.main())
    except KeyboardInterrupt:
        print(
            f"{Fore.CYAN + Style.BRIGHT}[ {datetime.now().astimezone(wib).strftime('%x %X %Z')} ]{Style.RESET_ALL}"
            f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}"
            f"{Fore.RED + Style.BRIGHT}Bot Stopped By User.{Style.RESET_ALL}"
)
