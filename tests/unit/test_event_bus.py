from network.event_bus import InMemoryEventBus


def test_event_bus_publishes_to_specific_and_global_subscribers():
    bus = InMemoryEventBus()
    seen = []

    bus.subscribe(lambda event: seen.append(("all", event.type)))
    bus.subscribe(lambda event: seen.append(("move", event.payload["accepted"])), "move_requested")

    bus.publish("move_requested", {"accepted": True})

    assert seen == [("all", "move_requested"), ("move", True)]

