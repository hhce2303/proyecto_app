class UserBoard:
    def __init__(self):
        self.sheet = None
        from prin import create_user_table_tab
        self.create_user_table_tab = create_user_table_tab.__get__(self)
        
if __name__ == "__main__":
    user_board = UserBoard()
    user_board.create_user_table_tab(
        tab=None, 
        tabla="Usuarios", 
        data={'headers': ['ID', 'Name'], 'rows': [[1, 'Alice'], [2, 'Bob']]}, 
        rol="admin"
    )