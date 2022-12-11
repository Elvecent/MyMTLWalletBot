from typing import List

from aiogram import Router, types
from aiogram.filters import Text
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from stellar_sdk import Asset

from keyboards.common_keyboards import get_return_button, get_kb_yesno_send_xdr, get_kb_return
from mytypes import Balance
from utils.aiogram_utils import send_message, my_gettext, logger
from utils.stellar_utils import stellar_get_balances, stellar_add_trust, stellar_get_user_account, \
    stellar_is_free_wallet, public_issuer, get_good_asset_list


class DelAssetCallbackData(CallbackData, prefix="DelAssetCallbackData"):
    answer: str


class AddAssetCallbackData(CallbackData, prefix="DelAssetCallbackData"):
    answer: str


class StateAddAsset(StatesGroup):
    sending_code = State()
    sending_issuer = State()


router = Router()


@router.callback_query(Text(text=["WalletSetting"]))
async def cmd_wallet_setting(callback: types.CallbackQuery, state: FSMContext):
    msg = my_gettext(callback, 'wallet_setting_msg')
    buttons = [
        [types.InlineKeyboardButton(text=my_gettext(callback, 'kb_add_asset'), callback_data="AddAssetMenu")],
        [types.InlineKeyboardButton(text=my_gettext(callback, 'kb_buy'), callback_data="NotImplemented")],
        [types.InlineKeyboardButton(text=my_gettext(callback, 'kb_get_key'), callback_data="NotImplemented")],
        [types.InlineKeyboardButton(text=my_gettext(callback, 'kb_set_password'), callback_data="NotImplemented")],
        [types.InlineKeyboardButton(text=my_gettext(callback, 'kb_remove_password'), callback_data="NotImplemented")],
        [types.InlineKeyboardButton(text=my_gettext(callback, 'change_lang'), callback_data="ChangeLang")],
        get_return_button(callback)
    ]

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    await send_message(callback, msg, reply_markup=keyboard)


@router.callback_query(Text(text=["AddAssetMenu"]))
async def cmd_add_asset(callback: types.CallbackQuery, state: FSMContext):
    msg = my_gettext(callback, 'delete_asset')
    buttons = [
        [types.InlineKeyboardButton(text=my_gettext(callback, 'kb_delete_one'), callback_data="DeleteAsset")],
        [types.InlineKeyboardButton(text=my_gettext(callback, 'kb_add_list'), callback_data="AddAsset")],
        [types.InlineKeyboardButton(text=my_gettext(callback, 'kb_add_expert'), callback_data="AddAssetExpert")],
        get_return_button(callback)
    ]

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    await send_message(callback, msg, reply_markup=keyboard)


########################################################################################################################
########################################################################################################################
########################################################################################################################

@router.callback_query(Text(text=["DeleteAsset"]))
async def cmd_add_asset_del(callback: types.CallbackQuery, state: FSMContext):
    asset_list = stellar_get_balances(callback.from_user.id)

    kb_tmp = []
    for token in asset_list:
        kb_tmp.append([types.InlineKeyboardButton(text=f"{token.asset_code} ({token.balance})",
                                                  callback_data=DelAssetCallbackData(
                                                      answer=token.asset_code).pack()
                                                  )])
    kb_tmp.append(get_return_button(callback))
    msg = my_gettext(callback, 'delete_asset2')
    await send_message(callback, msg, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb_tmp))
    await state.update_data(assets=asset_list)
    await callback.answer()


@router.callback_query(DelAssetCallbackData.filter())
async def cq_swap_choose_token_from(callback: types.CallbackQuery, callback_data: DelAssetCallbackData,
                                    state: FSMContext):
    answer = callback_data.answer
    data = await state.get_data()
    asset_list: List[Balance] = data['assets']

    asset = list(filter(lambda x: x.asset_code == answer, asset_list))
    if asset:
        await state.update_data(send_asset_code=asset[0].asset_code,
                                send_asset_issuer=asset[0].asset_issuer)
        # todo send last coins
        xdr = stellar_add_trust(stellar_get_user_account(callback.from_user.id).account.account_id,
                                Asset(asset[0].asset_code, asset[0].asset_issuer),
                                delete=True)

        msg = my_gettext(callback, 'confirm_close_asset').format(asset[0].asset_code, asset[0].asset_issuer)
        await state.update_data(xdr=xdr)

        await send_message(callback, msg, reply_markup=get_kb_yesno_send_xdr(callback))
    else:
        await callback.answer(my_gettext(callback, "bad_data"), show_alert=True)
        logger.info(f'error add asset {callback.from_user.id} {answer}')

    await callback.answer()


########################################################################################################################
########################################################################################################################
########################################################################################################################

@router.callback_query(Text(text=["AddAsset"]))
async def cmd_add_asset_add(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if stellar_is_free_wallet(user_id) and (len(stellar_get_balances(user_id)) > 2):
        await send_message(user_id, my_gettext(user_id, 'only_3'), reply_markup=get_kb_return(user_id))
        return False

    good_asset = get_good_asset_list()
    for item in stellar_get_balances(user_id):
        found = list(filter(lambda x: x.asset_code == item.asset_code, good_asset))
        if len(found) > 0:
            good_asset.remove(found[0])

    if len(good_asset) == 0:
        await send_message(user_id, my_gettext(user_id, 'have_all'), reply_markup=get_kb_return(user_id))
        return False

    kb_tmp = []
    for key in good_asset:
        kb_tmp.append([types.InlineKeyboardButton(text=f"{key.asset_code}",
                                                  callback_data=AddAssetCallbackData(
                                                      answer=key.asset_code).pack()
                                                  )])
    kb_tmp.append(get_return_button(callback))
    await send_message(callback, my_gettext(user_id, 'open_asset'),
                       reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb_tmp))

    await state.update_data(assets=good_asset)


@router.callback_query(AddAssetCallbackData.filter())
async def cq_add_asset(callback: types.CallbackQuery, callback_data: AddAssetCallbackData,
                       state: FSMContext):
    answer = callback_data.answer
    data = await state.get_data()
    asset_list: List[Balance] = data['assets']

    asset = list(filter(lambda x: x.asset_code == answer, asset_list))
    if asset:
        await state.update_data(send_asset_code=asset[0].asset_code,
                                send_asset_issuer=asset[0].asset_issuer)
        await cmd_add_asset_end(callback.message.chat.id, state)
    else:
        await callback.answer(my_gettext(callback, "bad_data"), show_alert=True)
        logger.info(f'error add asset {callback.from_user.id} {answer}')

    await callback.answer()


########################################################################################################################
########################################################################################################################
########################################################################################################################

@router.callback_query(Text(text=["AddAssetExpert"]))
async def cmd_add_asset_expert(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if stellar_is_free_wallet(user_id) and (len(stellar_get_balances(user_id)) > 2):
        await send_message(user_id, my_gettext(user_id, 'only_3'), reply_markup=get_kb_return(user_id))
        return False

    await state.set_state(StateAddAsset.sending_code)
    msg = my_gettext(user_id, 'send_code')
    await send_message(user_id, msg, reply_markup=get_kb_return(user_id))
    await callback.answer()


@router.message(StateAddAsset.sending_code)
async def cmd_swap_sum(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    asset_code = message.text
    await state.update_data(send_asset_code=asset_code)

    await state.set_state(StateAddAsset.sending_issuer)

    msg = my_gettext(user_id, 'send_issuer').format(public_issuer)
    await send_message(user_id, msg, reply_markup=get_kb_return(user_id))


@router.message(StateAddAsset.sending_issuer)
async def cmd_swap_sum(message: types.Message, state: FSMContext):
    await state.update_data(send_asset_issuer=message.text)
    await cmd_add_asset_end(message.chat.id, state)


########################################################################################################################
########################################################################################################################
########################################################################################################################


async def cmd_add_asset_end(chat_id: int, state: FSMContext):
    data = await state.get_data()
    asset_code = data.get('send_asset_code', 'XLM')
    asset_issuer = data.get('send_asset_issuer', '')

    xdr = stellar_add_trust(stellar_get_user_account(chat_id).account.account_id, Asset(asset_code, asset_issuer))

    msg = my_gettext(chat_id, 'confirm_asset').format(asset_code, asset_issuer)

    await state.update_data(xdr=xdr)
    await send_message(chat_id, msg, reply_markup=get_kb_yesno_send_xdr(chat_id))
