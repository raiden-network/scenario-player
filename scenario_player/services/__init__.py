"""Module providing micro services for the raiden Scenario Player.

Each service package includes blueprints and schemas for the service's domain.

    :mod:`scenario_player.services.common`
    Module containing generic code used across two or more services. It contains
    common blueprints, metrics instrumentation, schema validators and serializer
    and factories to construct flask apps and its core components.

    :mod:`scenario_player.services.utils`
    Utilities package supplying service-agnostic objects, such as classes and functions,
    which do not directly relate to :mod:`flask` or :mod:`marshmallow`.
    Among these are the :class:`scenario_player.services.utils.JSONRedis` class, as
    well as its mock counterpart used in testing.

"""