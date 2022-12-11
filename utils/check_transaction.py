import app_logger
import fb

if 'logger' not in globals():
    logger = app_logger.get_logger("MyMTLWalletBot_check_transaction")


def cmd_add_message(user_id, user_message):
    fb.execsql('insert into mymtlwalletbot_messages (user_id, user_message) values (?,?)', (user_id, user_message))


def cmd_check_and_send():
    record = fb.execsql('select first 1 user_transaction_id, user_id, user_transaction ' +
                        'from mymtlwalletbot_transactions where transaction_state = 0')
    if record:

        from utils.lang_utils import my_gettext
        from utils.stellar_utils import stellar_send
        transaction_id, user_id, xdr = record[0]
        fb.execsql('update mymtlwalletbot_transactions set transaction_state = 1 where user_transaction_id = ?',
                   (transaction_id,))
        try:
            logger.info(['xdr', xdr])
            resp = stellar_send(xdr)
            fb.execsql('update mymtlwalletbot_transactions set transaction_state = 2, transaction_response = ? ' +
                       'where user_transaction_id = ?',
                       (str(resp), transaction_id))
            cmd_add_message(user_id, my_gettext(user_id, "send_good"))

        except Exception as ex:
            logger.info(['error', ex])
            fb.execsql('update mymtlwalletbot_transactions set transaction_state = 3, transaction_response = ? ' +
                       'where user_transaction_id = ?',
                       (str(ex), transaction_id))
            cmd_add_message(user_id, my_gettext(user_id, "send_error"))


if __name__ == "__main__":
    cmd_check_and_send()
