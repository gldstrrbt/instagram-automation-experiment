import nodriver as uc
from nodriver.cdp import fetch
from nodriver.core.config import find_chrome_executable
from nodriver import *
import requests, pyautogui, json, time, win32gui, re, os, asyncio, logging, pytz, shutil, os, csv, re, yaml, itertools
from asyncio import iscoroutine, iscoroutinefunction
from datetime import datetime
from dateutil import parser as date_parser
from bs4 import BeautifulSoup

logger = logging.getLogger("uc.connection")
logging.basicConfig(level=30)

COOKIE_FILE_NAME = ".session.dat"
tab = None

async def listener_loop(self):
    while True:
        try:
            msg = await asyncio.wait_for(
                self.connection.websocket.recv(), self.time_before_considered_idle
            )
        except asyncio.TimeoutError:
            self.idle.set()
            continue
        except (Exception,) as e:
            logger.debug(
                "connection listener exception while reading websocket:\n%s", e
            )
            break

        if not self.running:
            break

        self.idle.clear()
        message = json.loads(msg)
        if "id" in message:
            if message["id"] in self.connection.mapper:
                tx = self.connection.mapper[message["id"]]
                logger.debug("got answer for %s", tx)
                tx(**message)
                self.connection.mapper.pop(message["id"])
        else:
            try:
                event = cdp.util.parse_json_event(message)
                event_tx = uc.connection.EventTransaction(event)
                if not self.connection.mapper:
                    self.connection.__count__ = itertools.count(0)
                event_tx.id = next(self.connection.__count__)
                self.connection.mapper[event_tx.id] = event_tx
            except Exception as e:
                logger.info(
                    "%s: %s  during parsing of json from event : %s"
                    % (type(e).__name__, e.args, message),
                    exc_info=True,
                )
                continue
            except KeyError as e:
                logger.info("some lousy KeyError %s" % e, exc_info=True)
                continue
            try:
                if type(event) in self.connection.handlers:
                    callbacks = self.connection.handlers[type(event)]
                else:
                    continue
                if not len(callbacks):
                    continue
                for callback in callbacks:
                    try:
                        if iscoroutinefunction(callback) or iscoroutine(callback):
                            await callback(event)
                        else:
                            callback(event)
                    except Exception as e:
                        logger.warning(
                            "exception in callback %s for event %s => %s",
                            callback,
                            event.__class__.__name__,
                            e,
                            exc_info=True,
                        )
                        raise
            except asyncio.CancelledError:
                break
            except Exception:
                raise
            continue


def uc_fix(uc: uc):
    uc.core.connection.Listener.listener_loop = listener_loop


async def enter_key(tab):
    await tab.send(cdp.input_.dispatch_key_event(
        type_="keyDown", key="Enter", code="Enter",
        windows_virtual_key_code=13, native_virtual_key_code=13
    ))
    await tab.send(cdp.input_.dispatch_key_event(
        type_="keyUp", key="Enter", code="Enter",
        windows_virtual_key_code=13, native_virtual_key_code=13
    ))


def webhook_alert(webhook_message):
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        raise RuntimeError("Set DISCORD_WEBHOOK_URL before using webhook_alert().")
    message = {"content": webhook_message}
    requests.post(webhook_url, json=message)


async def testing_browser_start():
    global tab
    driver = await uc.start()
    uc_fix(uc)
    try:
        tab = await driver.get("https://www.instagram.com/")
    except:
        pass


async def login_to_insta(email, password):
    global tab
    driver = await uc.start()
    uc_fix(uc)
    try:
        tab = await driver.get("https://www.instagram.com/")
        await tab.sleep(6)

        try:
            print("Attempting primary login form...")
            start_time = time.time()
            max_wait_time = 3

            email_input = None
            password_input = None
            submit_btn = None

            while time.time() - start_time < max_wait_time:
                try:
                    email_input = await tab.select('input[name="username"]')
                    if email_input:
                        password_input = await tab.select('input[name="password"]')
                    if password_input:
                        submit_btn = await tab.select('button[type="submit"]')
                        break
                except:
                    pass
                await tab.sleep(0.5)

            if email_input and password_input and submit_btn:
                print("Primary login detected")
                await email_input.send_keys(email)
                await password_input.send_keys(password)
                await tab.sleep(1)
                await submit_btn.click()
                print("Submitted primary login")
            else:
                print("trying secondary form...")
                email_input = await tab.select('input[name="email"]')
                password_input = await tab.select('input[name="password"]')
                print(email_input)
                print(password_input)

                if email_input and password_input:
                    print("Secondary login detected")
                    await email_input.send_keys(email)
                    await password_input.send_keys(password)
                    login_button = await tab.select('div[role="none"] span:contains("Log in")')
                    if login_button:
                        await login_button.click()
                        print("Submitted secondary login form")
                    else:
                        print("Secondary login button not found")
                else:
                    print("Neither primary nor secondary login form found")

            await tab.sleep(10)
        except Exception as e:
            print(f"Error during login attempt: {str(e)}")
    except Exception as e:
        print(f"Error during page load: {str(e)}")


async def get_page_html():
    try:
        print("Getting page html")
        html_content = await tab.get_content()
        soup = BeautifulSoup(html_content, 'html.parser')
        print("html formatted for parsing")
        return soup
    except Exception as e:
        print(f"bs4 failed to get page content: {str(e)}")


async def scroll_a_bunch(tab, number_of_times_to_scroll):
    scroll_iter = 0
    while scroll_iter <= number_of_times_to_scroll:
        await tab.evaluate("window.scrollBy(0, 2000);")
        scroll_iter += 1
        await tab.sleep(1)


async def get_insta_feed_url(tab, page_url):
    tab = await tab.get("https://www.instagram.com")
    try:
        print("*"*50)
        print("going to explore feed")
        await tab.sleep(2)
        tab = await tab.get(page_url)
        await tab.sleep(10)
        print("explore feed loaded")
        print("*"*50)
    except:
        print("! failed to load explore feed !")
        print("*"*50)
        pass


async def get_all_likes_button_links_from_homefeed(tab):
    try:
        likes_links = await tab.select_all('a[role="link"]')
        print("likes_links: ", str(likes_links))
    except:
        pass


async def check_likes_dialog_open_homefeed(tab):
    try:
        likes_dialog = await tab.select('[role="dialog"]')
        print("likes_dialog: ", str(likes_dialog))
    except:
        pass

    if len(likes_dialog) > 0:
        try:
            likes_header = await likes_dialog.select('h2')
            print("likes_header: ", str(likes_header))
        except:
            pass


async def get_all_users_from_likes_link_page(tab, likes_url):
    try:
        tab = await driver.get("https://www.instagram.com"+str(likes_url))
        await tab.sleep(6)
        users = await tab.select('main[role="main"]')
        print("get_all_users_from_likes_link(): likes_links: users: ", str(users))
    except:
        pass


async def get_all_posts_urls_explorefeed(tab):
    explore_post_objects = []
    await scroll_a_bunch(tab, 10)
    page_content = await get_page_html()
    explore_posts = page_content.select('a[role="link"]')

    for a in explore_posts:
        link_tag_href = a.get("href")
        print("*"*50)
        print(link_tag_href)
        print("*"*50)
        if not link_tag_href:
            continue

        if "/p/" in link_tag_href and "/liked_by" not in link_tag_href:
            print("get_all_posts_urls_explorefeed: a: ", str(a))
            post_img_attr = get_explorefeed_img_per_post(a)
            post_obj = {
                "post_url": link_tag_href,
                "post_img_data": {
                    "img_href":post_img_attr[0],
                    "img_alt_text":post_img_attr[1]
                }
            }
            explore_post_objects.append(post_obj)
    print("get_all_posts_urls_explorefeed: explore_posts: ", str(explore_posts))
    print("get_all_posts_urls_explorefeed: explore_post_objects: ", str(explore_post_objects))
    return explore_post_objects


async def get_opened_post_dialog_body_explorefeed(tab):
    try:
        likes_dialog = await tab.select('article[role="presentation"]')
        print("likes_dialog: ", str(likes_dialog))
    except:
        pass

    if len(likes_dialog) > 0:
        try:
            likes_header = await likes_dialog.select('h2')
            print("likes_header: ", str(likes_header))
        except:
            pass


async def get_likes_button_link_from_post_dialog_explorefeed(tab):
    try:
        likes_dialog = await tab.select('[role="dialog"]')
        print("likes_dialog: ", str(likes_dialog))
    except:
        pass

    if len(likes_dialog) > 0:
        try:
            likes_header = await likes_dialog.select('h2')
            print("likes_header: ", str(likes_header))
        except:
            pass


def get_explorefeed_img_per_post(html_content):
    img_urls = []
    post_imgs = html_content.select("img")
    img_alt = None
    for a in post_imgs:
        img_src = a.get("src")
        if img_src:
            img_src = img_src.replace("&amp;", "&")
            img_urls.append(img_src)
        img_alt = a.get("alt")
    return [img_urls, img_alt]


async def find_lowest_parent_with_follow_and_canvas(tab):
    try:
        html_content = await tab.get_content()
        soup = BeautifulSoup(html_content, 'html.parser')
        follow_texts = []
        for element in soup.find_all(string=lambda text: text and "Follow" in text):
            follow_texts.append(element)
        for button in soup.find_all(['button', 'span', 'div']):
            if button.text and "Follow" in button.text and button.text.strip() == "Follow":
                follow_texts.append(button)
        canvas_elements = soup.find_all('canvas')
        if not follow_texts:
            print("No 'Follow' text elements found")
            return None
        if not canvas_elements:
            print("No canvas elements found")
            return None
        print(f"Found {len(follow_texts)} potential 'Follow' elements and {len(canvas_elements)} canvas elements")
        best_parent = None
        min_level = float('inf')
        for follow_element in follow_texts:
            for canvas in canvas_elements:
                follow_ancestors = []
                current = follow_element
                while current and current.parent:
                    current = current.parent
                    follow_ancestors.append(current)
                canvas_ancestors = []
                current = canvas
                while current and current.parent:
                    current = current.parent
                    canvas_ancestors.append(current)
                for i, follow_parent in enumerate(follow_ancestors):
                    if i >= min_level:
                        continue
                    for j, canvas_parent in enumerate(canvas_ancestors):
                        if i + j >= min_level:
                            continue
                        if follow_parent is canvas_parent:
                            total_level = i + j
                            if total_level < min_level:
                                min_level = total_level
                                best_parent = follow_parent
                                print(f"Found potential parent at level {total_level}")
                                break
        if best_parent:
            print(f"Best parent found: {best_parent.name} with class {best_parent.get('class', 'no-class')}")
            return best_parent
        print("No suitable common parent found")
        return None
    except Exception as e:
        print(f"Error in find_lowest_parent_with_follow_and_canvas: {str(e)}")
        return None


async def get_follow_button_container(tab):
    try:
        html_content = await tab.get_content()
        soup = BeautifulSoup(html_content, 'html.parser')
        potential_containers = []
        for container in soup.find_all(['div', 'section', 'article']):
            has_follow = False
            for btn in container.find_all(['button', 'a']):
                if btn.text and btn.text.strip() == "Follow":
                    has_follow = True
                    break
            if has_follow and container.find('canvas'):
                depth = len(container.find_all())
                potential_containers.append({'element': container, 'depth': depth})
        if potential_containers:
            potential_containers.sort(key=lambda x: x['depth'], reverse=True)
            best_match = potential_containers[0]['element']
            print(f"Found container with {potential_containers[0]['depth']} children")
            return best_match
        print("No container found with both Follow button and canvas")
        return None
    except Exception as e:
        print(f"Error in get_follow_button_container: {str(e)}")
        return None


async def get_post_page_data(tab):
    a = get_follow_button_from_profile(tab)


async def main():
    global tab
    await testing_browser_start()
    await get_insta_feed_url(tab, "https://instagram.com/p/DHUKwAISVGs/")
    await tab.sleep(5)
    await find_lowest_parent_with_follow_and_canvas(tab)
    await get_follow_button_container(tab)


if __name__ == "__main__":
    asyncio.run(main())
