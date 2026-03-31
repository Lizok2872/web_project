class Login:
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    
    with app.app_context():
        db.create_all()
    
    
    
    async def fetch_recipe_data_async(session, recipe_id):
        url = f"http://localhost:8080/api/v1/recipes/{recipe_id}"
        async with session.get(url) as response:
            return await response.json()
    
    
    def run_async_recipe_fetch(recipe_ids):
        async def fetch_all():
            async with aiohttp.ClientSession() as session:
                tasks = [fetch_recipe_data_async(session, rid) for rid in recipe_ids]
                results = await asyncio.gather(*tasks)
                return results
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(fetch_all())
    
    
    
