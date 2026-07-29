from observer_manifold import ObserverState
async def observer_tracking_middleware(request, call_next):
    observer = ObserverState.capture("api", (0.0,0.0,0.0))
    request.state.observer = observer
    response = await call_next(request)
    return response
