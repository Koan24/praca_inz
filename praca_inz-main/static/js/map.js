fetch('/api/punkty')
    .then(response => response.json())
    .then(data => {
        console.log("Dane z API:", data); // Wyświetl dane w konsoli przeglądarki

        // Dodanie punktów na mapie
        if (data.features && data.features.length > 0) {
            data.features.forEach(feature => {
                if (feature.geometry && feature.geometry.coordinates) {
                    const marker = L.marker([
                        feature.geometry.coordinates[1], // Lat
                        feature.geometry.coordinates[0]  // Lng
                    ]).addTo(map);

                    // Dodanie popupu
                    marker.bindPopup(`
                        <b>${feature.properties.nazwa}</b><br>
                        Poziom wody: ${feature.properties.poziom_wody}<br>
                        <img src="/${feature.properties.zdjecie}" alt="Zdjęcie" style="width:100px;height:auto;">
                    `);
                } else {
                    console.error("Brak geometrii w punkcie:", feature);
                }
            });
        } else {
            console.error("Brak danych w API lub format jest nieprawidłowy.");
        }
    })
    .catch(error => console.error('Błąd podczas ładowania danych:', error));