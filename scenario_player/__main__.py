from gevent import monkey  # isort:skip

monkey.patch_all()  # isort:skip


from .main import main

if __name__ == "__main__":
    main()
