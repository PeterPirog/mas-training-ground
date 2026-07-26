# mas-training-ground

> **Status:** Aktywne repozytorium szkoleniowe z agentów i workflow LLM.

## Cel i rzeczywista zawartość

Projekt organizuje serię misji edukacyjnych: structured outputs, Pydantic, tool calling, jawny stan workflow, prompt caching, LangGraph, actor–critic oraz human-in-the-loop. Materiał łączy rozbudowane instrukcje z małymi implementacjami.

## Zakres potwierdzony w repozytorium

- pełne materiały fazy pierwszej z kodem i zapisem przebiegów
- osobne misje tool calling, LangGraph, actor–critic i human-in-loop
- notebook kursowy oraz wspólne narzędzia i przykładowa konfiguracja środowiska
- pliki Markdown opisujące cele, kontrakty danych i zasady bezpieczeństwa wykonania

## Gdzie leży wartość merytoryczna

- największą wartością jest spójny program nauki przechodzący od odpowiedzi strukturalnych do sterowanych workflow
- nacisk na walidację po stronie aplikacji i jawny stan jest praktycznie istotny dla niezawodnych agentów
- połączenie teorii, kodu i śladów uruchomień ułatwia samodzielną naukę

## Ograniczenia rzetelnej oceny

- część materiału zależy od szybko zmieniających się API i wymaga okresowej aktualizacji
- repozytorium nie pokazuje jeszcze jednego końcowego systemu integrującego wszystkie misje
- zewnętrzne materiały i adaptowane przykłady powinny mieć konsekwentne źródła i atrybucję

## Jak zweryfikować wartość projektu

- uruchamiać misje kolejno w czystym środowisku i zachowywać przykładowe oczekiwane wyniki
- testować błędne dane, odmowę narzędzia i wznowienie stanu, nie tylko happy path
- oceniać postęp przez niezawodność kontraktów i workflow, nie przez efektowność odpowiedzi modelu

## Uwagi

Opis sporządzono na podstawie plików obecnych na domyślnej gałęzi repozytorium. Nie zakłada on funkcji, wyników ani gotowości produkcyjnej, których nie da się potwierdzić z zawartości.

Obecność kodu lub danych nie oznacza automatycznie gotowości produkcyjnej, poprawności naukowej ani prawa do redystrybucji materiałów zewnętrznych. Licencję i pochodzenie danych należy oceniać na podstawie odpowiednich plików źródłowych oraz warunków ich dostawców.
