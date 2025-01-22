import os
from django.shortcuts import render, redirect
import pandas as pd
from textblob import TextBlob

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_and_clean_data():
    reviews_path = os.path.join(BASE_DIR, 'datasets', 'customer_reviews.csv')
    books_path = os.path.join(BASE_DIR, 'datasets', 'books.csv')

    print(f"Reviews path: {reviews_path}")
    print(f"Books path: {books_path}")

    books = pd.DataFrame()  # Inisialisasi untuk mencegah error saat exception
    reviews = pd.DataFrame()

    try:
        books = pd.read_csv(books_path)
        reviews = pd.read_csv(reviews_path)

        print("\nBooks DataFrame columns before rename:", books.columns.tolist())
        print("\nReviews DataFrame columns before rename:", reviews.columns.tolist())

        # Sesuaikan kolom untuk books
        books = books[['book title', 'genre', 'rating']]
        books.rename(columns={'book title': 'book name'}, inplace=True)

        print("\nBooks DataFrame columns after rename:", books.columns.tolist())

        # Konversi rating ke numeric, hapus baris dengan rating kosong
        books['rating'] = pd.to_numeric(books['rating'], errors='coerce')
        books = books.dropna(subset=['rating'])
        
        # Pisahkan genre jika ada multiple genre
        books['genre'] = books['genre'].fillna('Unknown')
        
        # Sesuaikan kolom untuk reviews
        reviews = reviews[['book name', 'review description']]
        
        # Bersihkan data
        books.drop_duplicates(inplace=True)
        reviews.drop_duplicates(inplace=True)

        print("\nProcessed Books DataFrame:")
        print(books.head())
        print("\nProcessed Reviews DataFrame:")
        print(reviews.head())

        return reviews, books

    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame(), pd.DataFrame()

def analyze_sentiment(reviews):
    def calculate_sentiment(review):
        if pd.isna(review):
            return 0
        blob = TextBlob(str(review))
        return blob.sentiment.polarity

    reviews['sentiment_score'] = reviews['review description'].apply(calculate_sentiment)
    return reviews

def save_recommendations_to_file(recommendations):
    file_path = os.path.join(BASE_DIR, 'datasets', 'recommendations.txt')
    with open(file_path, 'w') as file:
        for book in recommendations:
            file.write(f"{book['book name']};{book['genre']};{book['rating']}\n")

def recommend_based_on_book(book_name, books, reviews, top_n=10):
    print("\nBooks DataFrame columns:", books.columns.tolist())
    print("\nSample of books data:")
    print(books.head().to_string())
    
    matching_books = books[books['book name'].str.contains(book_name, case=False, na=False)]
    print("\nMatching books data:")
    print(matching_books.to_string())
    
    if matching_books.empty:
        return pd.DataFrame()

    genres = matching_books['genre'].str.split(',').explode().str.strip().unique()
    
    sentiment_avg = reviews.groupby('book name')['sentiment_score'].mean().reset_index()
    books = books.merge(sentiment_avg, on='book name', how='left').fillna({'sentiment_score': 0})
    
    genre_books = books[books['genre'].str.contains('|'.join(genres), case=False, na=False) & 
                       ~books['book name'].isin(matching_books['book name'])].copy()
    
    if not genre_books.empty:
        genre_books['final_score'] = genre_books['rating'] * 0.7 + genre_books['sentiment_score'] * 0.3
        genre_recommendations = genre_books.sort_values(by='final_score', ascending=False).head(top_n - len(matching_books))
    else:
        genre_recommendations = pd.DataFrame()

    final_recommendations = pd.concat([matching_books, genre_recommendations]).head(top_n)
    
    # Pastikan semua kolom terisi
    final_recommendations = final_recommendations.fillna({
        'book name': 'Unknown Title',
        'genre': 'Unknown Genre',
        'rating': 0.0
    })
    
    recommendations_dict = final_recommendations.to_dict('records')
    save_recommendations_to_file(recommendations_dict)
    
    return recommendations_dict

def save_user_input(username, choice, input_data, recommended_books):
    try:
        dataset_dir = os.path.join(BASE_DIR, 'datasets')
        if not os.path.exists(dataset_dir):
            os.makedirs(dataset_dir)
            print(f"Created directory {dataset_dir}")
        
        file_path = os.path.join(dataset_dir, 'user_inputs.txt')
        print(f"Attempting to write to {file_path}")
        
        with open(file_path, 'a', encoding='utf-8') as file:
            file.write(f"Nama: {username}\n")
            file.write(f"Pilih Opsi: {choice}\n")
            file.write(f"Masukkan Judul Buku: {input_data}\n")
            file.write("Rekomendasi:\n")
            file.write(f"{'Judul Buku'.ljust(30)}{'Genre'.ljust(20)}{'Rating'.ljust(10)}\n")
            
            for book in recommended_books:
                book_title = book.get('book name', 'Unknown Title').ljust(30)
                genre = book.get('genre', 'Unknown Genre').ljust(20)
                rating = str(book.get('rating', 'N/A')).ljust(10)
                file.write(f"{book_title}{genre}{rating}\n")
            file.write("\n")  # Add a newline for separation between entries
            
            print("Data written successfully.")
            
    except Exception as e:
        print(f"Error saving user input: {e}")

def load_recommendations_from_file():
    file_path = os.path.join(BASE_DIR, 'datasets', 'recommendations.txt')
    recommendations = []
    with open(file_path, 'r') as file:
        for line in file:
            try:
                book_name, genre, rating = line.strip().split(';')
                recommendations.append({'book_name': book_name, 'genre': genre, 'rating': float(rating)})
            except ValueError:
                print(f"Skipping line due to formatting issues: {line}")
    return recommendations

def input_page(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        choice = request.POST.get('choice')
        input_data = request.POST.get('input_data')

        reviews, books = load_and_clean_data()
        reviews = analyze_sentiment(reviews)

        if choice == '2':
            recommend_based_on_book(input_data, books, reviews)
            recommendations = load_recommendations_from_file()
            return render(request, 'book_app/recommendations.html', {'username': username, 'recommendations': recommendations})
        else:
            return redirect('input_page')

    return render(request, 'book_app/input.html')



