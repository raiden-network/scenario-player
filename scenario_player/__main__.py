from gevent import monkey  # isort:skip

monkey.patch_all()  # isort:skip


from .main import main, pack_logs

if __name__ == "__main__":
    main()
