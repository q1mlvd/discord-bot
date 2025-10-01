// Загрузка статистики
async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const stats = await response.json();
        
        document.getElementById('total-users').textContent = stats.total_users;
        document.getElementById('total-nfts').textContent = stats.total_nfts;
        document.getElementById('total-volume').textContent = stats.total_volume.toLocaleString() + ' монет';
    } catch (error) {
        console.error('Ошибка загрузки статистики:', error);
    }
}

// Загрузка данных пользователя
async function loadUserData() {
    const userId = document.getElementById('user-id').value;
    if (!userId) {
        alert('Введите ID пользователя');
        return;
    }

    try {
        const response = await fetch(`/api/user/${userId}`);
        const userData = await response.json();
        
        const userDiv = document.getElementById('user-data');
        if (userData.error) {
            userDiv.innerHTML = `<p>❌ Пользователь не найден</p>`;
        } else {
            userDiv.innerHTML = `
                <h3>Данные пользователя ID: ${userId}</h3>
                <p>💰 Баланс: ${userData.balance} монет</p>
                <p>⭐ Уровень: ${userData.level}</p>
            `;
        }
    } catch (error) {
        console.error('Ошибка загрузки пользователя:', error);
    }
}

// Загрузка NFT маркетплейса
async function loadMarketplace() {
    try {
        const response = await fetch('/api/marketplace');
        const nfts = await response.json();
        
        const nftList = document.getElementById('nft-list');
        nftList.innerHTML = '';
        
        if (nfts.length === 0) {
            nftList.innerHTML = '<p>😔 На маркетплейсе пока нет NFT</p>';
            return;
        }
        
        nfts.forEach(nft => {
            const nftCard = document.createElement('div');
            nftCard.className = 'nft-card';
            nftCard.innerHTML = `
                <h4>${nft.name}</h4>
                <p>Коллекция: ${nft.collection}</p>
                <p>💰 Цена: ${nft.price} монет</p>
                <p>🆔 ID: ${nft.id}</p>
            `;
            nftList.appendChild(nftCard);
        });
    } catch (error) {
        console.error('Ошибка загрузки маркетплейса:', error);
    }
}

// Загрузка при старте
document.addEventListener('DOMContentLoaded', function() {
    loadStats();
    loadMarketplace();
});
