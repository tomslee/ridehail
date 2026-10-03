<?php
/*
 * Leaderboard for the lab's Game tab ("Just One More Shift…"): named top scores for each
 * board, where a board is one shift code + market + offer screen ("card":
 * helper, with the rate helper, or platform, the platform's card only). There
 * is no sign-in, so anyone can use any name; each name's best score is kept.
 *
 *   GET  ?code=2026-09-29&market=busy[&card=helper]
 *        -> {count, top: [{place, name, net_per_hour}]}
 *   POST {code, market, card, name, version, player: {...}}
 *        (player is the "player" block of ridehail.game results)
 *        -> {count, rank, best, top}
 *
 * Submissions are checked for internal consistency (net = earnings - costs,
 * a full 180-minute shift, and so on), so made-up numbers are rejected unless
 * they are made up carefully. Each network address may submit a limited
 * number of scores an hour; only a salted hash of the address is stored, and
 * it is erased after a day.
 *
 * Moderation: create a file "admin-token" (one line, a long random string) in
 * the data directory. Then
 *   GET  ?admin=TOKEN&code=...&market=...[&card=...]    lists every entry, with ids
 *   POST {action: "delete", token: TOKEN, id: N}   deletes one
 * Names containing any word listed (one per line) in "blocked-words.txt" in
 * the data directory are refused.
 *
 * Data directory: RIDEHAIL_DATA_DIR if set, otherwise "ridehail-data" three
 * levels above this file's real location, i.e. next to public_html (so it is
 * never served, and deploy.sh's rsync --delete never touches it). On
 * tomslee.net ~/public_html is a link to ~/domains/tomslee.net/public_html,
 * so it is /home/tomslee/domains/tomslee.net/ridehail-data. PHP must be able
 * to create and write it.
 *
 * See claude/game-mode.md (leaderboard) and docs/lab/modules/game-leaderboard.js.
 */

declare(strict_types=1);

const MARKETS = ['busy', 'normal', 'slow'];
const CARDS = ['helper', 'platform'];   // ridehail.game.CARDS
const SHIFT_MINUTES = 180.0;
const KM_PER_MINUTE = 0.37;      // ridehail.game.KM_PER_BLOCK: 0.37 km per block
const OPS_COST_PER_KM = 0.56;    // ridehail.game.GameParams.ops_cost_per_km
// Scores from earlier versions were made under different rules (running
// costs were $0.30/km before 2026.9.30.2; offers came from a flat rate card
// times a random factor before the Part 3 offer model; blocks were 0.5 km
// before the slower block of 5.8; the bots, whose seats change every shift,
// changed in 2026.10.3.1 to 2026.10.3.3) and are left out of the standings,
// though kept in the database. Raise this whenever a change to ridehail.game
// makes old scores incomparable.
const MIN_SCORING_VERSION = '2026.10.3.3';
// A change that affects some markets only raises their minimum here (above
// MIN_SCORING_VERSION; a lower entry has no effect). Busy and Slow became
// demand changes around Normal's fleet in 2026.10.3.0.
const MIN_SCORING_VERSION_BY_MARKET = [];
// Offers are at most 2.2x the rate card, so even a car that always had a
// rider could not gross much above $80/hr; allow some margin
const MAX_EARNINGS = 300.0;
const MIN_NET_PER_HOUR = -20.0;
const MAX_NAME_LENGTH = 20;
const MAX_CODE_LENGTH = 32;
const TOP_N = 10;
const SUBMISSIONS_PER_HOUR = 30;
const MAX_BODY_BYTES = 4096;
// Rounding in ridehail.game results: amounts to the cent, km to 0.1
const TOLERANCE = 0.03;
// A short built-in list; extend it with blocked-words.txt
const BLOCKED_WORDS = ['fuck', 'shit', 'cunt', 'nigger', 'faggot', 'retard', 'whore', 'slut'];

/** Length in characters (without depending on the mbstring extension). */
function text_length(string $text): int
{
    return function_exists('mb_strlen') ? mb_strlen($text) : (int) preg_match_all('/./su', $text);
}

function text_lower(string $text): string
{
    return function_exists('mb_strtolower') ? mb_strtolower($text) : strtolower($text);
}

function respond(int $status, array $body): void
{
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');
    echo json_encode($body);
    exit;
}

function fail(int $status, string $message): void
{
    respond($status, ['error' => $message]);
}

function data_dir(): string
{
    $dir = getenv('RIDEHAIL_DATA_DIR') ?: dirname(__DIR__, 3) . '/ridehail-data';
    if (!is_dir($dir) && !@mkdir($dir, 0700, true)) {
        fail(500, 'Leaderboard storage is not available');
    }
    return $dir;
}

function db(): PDO
{
    $pdo = new PDO('sqlite:' . data_dir() . '/leaderboard.sqlite');
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $pdo->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);
    $pdo->exec('PRAGMA busy_timeout = 3000');
    $pdo->exec(
        'CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY,
            created_at TEXT NOT NULL,
            shift_code TEXT NOT NULL,
            market TEXT NOT NULL,
            card TEXT NOT NULL,
            name TEXT NOT NULL,
            name_key TEXT NOT NULL,
            net_per_hour REAL NOT NULL,
            earnings REAL NOT NULL,
            costs REAL NOT NULL,
            offers INTEGER NOT NULL,
            accepts INTEGER NOT NULL,
            trips INTEGER NOT NULL,
            version TEXT,
            ip_hash TEXT
        )'
    );
    migrate_difficulty($pdo);
    $pdo->exec(
        'CREATE INDEX IF NOT EXISTS scores_board
         ON scores (shift_code, market, card, name_key, net_per_hour)'
    );
    return $pdo;
}

/**
 * Boards were once keyed by "difficulty" (rookie/pro). Rookie had the rate
 * helper, so its scores move to "helper"; Pro had a shorter timer and an
 * acceptance-rate rule, so its scores aren't comparable with either offer
 * screen and are deleted. Runs once, on the first request after the update.
 */
function migrate_difficulty(PDO $pdo): void
{
    $columns = array_column($pdo->query('PRAGMA table_info(scores)')->fetchAll(), 'name');
    if (!in_array('difficulty', $columns, true)) {
        return;
    }
    $pdo->beginTransaction();
    $pdo->exec("DELETE FROM scores WHERE difficulty <> 'rookie'");
    $pdo->exec("UPDATE scores SET difficulty = 'helper'");
    $pdo->exec('DROP INDEX IF EXISTS scores_board');
    $pdo->exec('ALTER TABLE scores RENAME COLUMN difficulty TO card');
    $pdo->commit();
}

/** A salted hash of the client's address, for rate limiting only. */
function ip_hash(): string
{
    $path = data_dir() . '/salt';
    if (!is_file($path)) {
        file_put_contents($path, bin2hex(random_bytes(16)), LOCK_EX);
        @chmod($path, 0600);
    }
    return hash('sha256', trim((string) file_get_contents($path)) . ($_SERVER['REMOTE_ADDR'] ?? ''));
}

function clean_code(mixed $code): string
{
    $code = is_string($code) ? trim($code) : '';
    if ($code === '' || text_length($code) > MAX_CODE_LENGTH || preg_match('/\p{C}/u', $code)) {
        fail(400, 'Invalid shift code');
    }
    return $code;
}

/**
 * The offer screen of a request. A page loaded before the offer-screen choice
 * sends difficulty=rookie (the rate helper) or nothing; its Pro is retired.
 */
function clean_card(array $request): string
{
    if (!array_key_exists('card', $request) && ($request['difficulty'] ?? 'rookie') === 'rookie') {
        return 'helper';
    }
    if (!array_key_exists('card', $request)) {
        fail(409, 'The game has been updated since this page loaded. Please reload it and play again.');
    }
    return clean_choice($request['card'], CARDS, 'helper', 'offer screen');
}

function clean_choice(mixed $value, array $allowed, string $default, string $what): string
{
    $value = $value ?? $default;
    if (!is_string($value) || !in_array($value, $allowed, true)) {
        fail(400, "Invalid $what");
    }
    return $value;
}

/** [display name, comparison key] or a 400 response. */
function clean_name(mixed $name): array
{
    $name = is_string($name) ? preg_replace('/\s+/u', ' ', trim($name)) : '';
    if ($name === '' || text_length($name) > MAX_NAME_LENGTH
        || !preg_match("/^[\\p{L}\\p{N}][\\p{L}\\p{N} _.'-]*$/u", $name)) {
        fail(400, 'Names can use letters, numbers, spaces and . _ \' - (up to 20 characters)');
    }
    $key = text_lower($name);
    // Compare without separators, so "f.u-c k" is caught too
    $squashed = preg_replace("/[ _.'-]/u", '', $key);
    $blocked = BLOCKED_WORDS;
    $extra = data_dir() . '/blocked-words.txt';
    if (is_file($extra)) {
        $blocked = array_merge($blocked, file($extra, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES));
    }
    foreach ($blocked as $word) {
        $word = text_lower(trim($word));
        if ($word !== '' && str_contains($squashed, $word)) {
            fail(400, 'Please choose a different name');
        }
    }
    return [$name, $key];
}

function number(array $data, string $key): float
{
    $value = $data[$key] ?? null;
    if (!is_int($value) && !is_float($value)) {
        fail(400, "Missing or invalid $key");
    }
    $value = (float) $value;
    if (!is_finite($value)) {
        fail(400, "Invalid $key");
    }
    return $value;
}

function near(float $a, float $b): bool
{
    return abs($a - $b) <= TOLERANCE;
}

/**
 * Check that a player result is a complete, internally consistent shift.
 * Returns the values to store.
 */
function check_player(mixed $player): array
{
    if (!is_array($player) || !is_array($player['minutes'] ?? null)) {
        fail(400, 'Missing result');
    }
    $minutes = $player['minutes'];
    $p1 = number($minutes, 'P1');
    $p2 = number($minutes, 'P2');
    $p3 = number($minutes, 'P3');
    $earnings = number($player, 'earnings');
    $costs = number($player, 'costs');
    $net = number($player, 'net');
    $km = number($player, 'km');
    $netPerHour = number($player, 'net_per_hour');
    $offers = number($player, 'offers');
    $accepts = number($player, 'accepts');
    $trips = number($player, 'trips_completed');

    $consistent =
        min($p1, $p2, $p3) >= 0
        && near($p1 + $p2 + $p3, SHIFT_MINUTES)
        && $km >= 0 && $km <= SHIFT_MINUTES * KM_PER_MINUTE + TOLERANCE
        && near($costs, $km * OPS_COST_PER_KM)
        && $earnings >= 0 && $earnings <= MAX_EARNINGS
        && near($net, $earnings - $costs)
        && near($netPerHour, $net / (SHIFT_MINUTES / 60.0))
        && $netPerHour >= MIN_NET_PER_HOUR
        && floor($offers) === $offers && floor($accepts) === $accepts && floor($trips) === $trips
        && $offers >= 0 && $offers <= SHIFT_MINUTES
        && $accepts >= 0 && $accepts <= $offers
        && $trips >= 0 && $trips <= $accepts
        // Paid minutes need accepted trips, and a trip needs paid minutes
        && ($p3 == 0.0 || $accepts > 0)
        && ($trips == 0.0 || $p3 > 0);
    if (!$consistent) {
        fail(422, 'That result does not add up to a complete shift');
    }
    return [
        'net_per_hour' => round($netPerHour, 2),
        'earnings' => round($earnings, 2),
        'costs' => round($costs, 2),
        'offers' => (int) $offers,
        'accepts' => (int) $accepts,
        'trips' => (int) $trips,
    ];
}

/** True if a score's version was played under the market's current rules. */
function current_rules(string $version, string $market): bool
{
    $minimum = MIN_SCORING_VERSION_BY_MARKET[$market] ?? MIN_SCORING_VERSION;
    return $version !== ''
        && version_compare($version, MIN_SCORING_VERSION, '>=')
        && version_compare($version, $minimum, '>=');
}

/**
 * Each name's best entry on a board, best first (ties: whoever got there
 * first). Worked out here rather than in SQL: boards are small, and this
 * avoids depending on the host SQLite's version and grouping rules.
 */
function standings(PDO $pdo, string $code, string $market, string $card): array
{
    $query = $pdo->prepare(
        'SELECT name, name_key, net_per_hour, version FROM scores
         WHERE shift_code = ? AND market = ? AND card = ?
         ORDER BY net_per_hour DESC, created_at ASC, id ASC'
    );
    $query->execute([$code, $market, $card]);
    $best = [];
    foreach ($query->fetchAll() as $row) {
        if (!current_rules((string) $row['version'], $market)) {
            continue;
        }
        $best[$row['name_key']] ??= ['name' => $row['name'], 'net_per_hour' => (float) $row['net_per_hour']];
    }
    return $best;
}

/** The top entries and the number of names on a board. */
function board(array $standings): array
{
    $top = [];
    foreach (array_slice(array_values($standings), 0, TOP_N) as $i => $entry) {
        $top[] = ['place' => $i + 1] + $entry;
    }
    return ['count' => count($standings), 'top' => $top];
}

function handle_get(): void
{
    $code = clean_code($_GET['code'] ?? null);
    $market = clean_choice($_GET['market'] ?? null, MARKETS, '', 'market');
    $card = clean_card($_GET);
    $pdo = db();
    if (isset($_GET['admin'])) {
        require_admin((string) $_GET['admin']);
        $all = $pdo->prepare(
            'SELECT id, created_at, name, net_per_hour, earnings, costs, offers, accepts, trips, version
             FROM scores WHERE shift_code = ? AND market = ? AND card = ?
             ORDER BY net_per_hour DESC'
        );
        $all->execute([$code, $market, $card]);
        respond(200, ['entries' => $all->fetchAll()]);
    }
    respond(200, board(standings($pdo, $code, $market, $card)));
}

function require_admin(string $token): void
{
    $path = data_dir() . '/admin-token';
    $expected = is_file($path) ? trim((string) file_get_contents($path)) : '';
    if (strlen($expected) < 16 || !hash_equals($expected, $token)) {
        fail(403, 'Not allowed');
    }
}

function handle_post(): void
{
    $raw = file_get_contents('php://input', false, null, 0, MAX_BODY_BYTES + 1);
    if ($raw === false || strlen($raw) > MAX_BODY_BYTES) {
        fail(413, 'Request too large');
    }
    $data = json_decode($raw, true);
    if (!is_array($data)) {
        fail(400, 'Expected JSON');
    }
    $pdo = db();

    if (($data['action'] ?? null) === 'delete') {
        require_admin((string) ($data['token'] ?? ''));
        $delete = $pdo->prepare('DELETE FROM scores WHERE id = ?');
        $delete->execute([(int) ($data['id'] ?? 0)]);
        respond(200, ['deleted' => $delete->rowCount()]);
    }

    $code = clean_code($data['code'] ?? null);
    $market = clean_choice($data['market'] ?? null, MARKETS, '', 'market');
    $card = clean_card($data);
    [$name, $nameKey] = clean_name($data['name'] ?? null);
    $version = substr(preg_replace('/[^0-9A-Za-z.+-]/', '', (string) ($data['version'] ?? '')), 0, 32);
    if (!current_rules($version, $market)) {
        fail(409, 'The game has been updated since this page loaded. Please reload it and play again.');
    }
    $score = check_player($data['player'] ?? null);

    $ipHash = ip_hash();
    $now = gmdate('Y-m-d\TH:i:s\Z');
    // Addresses are only needed for the hourly limit: forget them after a day
    $pdo->prepare('UPDATE scores SET ip_hash = NULL WHERE ip_hash IS NOT NULL AND created_at < ?')
        ->execute([gmdate('Y-m-d\TH:i:s\Z', time() - 86400)]);
    $recent = $pdo->prepare('SELECT COUNT(*) FROM scores WHERE ip_hash = ? AND created_at >= ?');
    $recent->execute([$ipHash, gmdate('Y-m-d\TH:i:s\Z', time() - 3600)]);
    if ((int) $recent->fetchColumn() >= SUBMISSIONS_PER_HOUR) {
        fail(429, 'Too many scores from here in the last hour; please try again later');
    }

    $insert = $pdo->prepare(
        'INSERT INTO scores (created_at, shift_code, market, card, name, name_key,
            net_per_hour, earnings, costs, offers, accepts, trips, version, ip_hash)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
    );
    $insert->execute([
        $now, $code, $market, $card, $name, $nameKey,
        $score['net_per_hour'], $score['earnings'], $score['costs'],
        $score['offers'], $score['accepts'], $score['trips'], $version, $ipHash,
    ]);

    // This name's best on the board, and its place: one more than the number
    // of names with a strictly better best
    $standings = standings($pdo, $code, $market, $card);
    $best = $standings[$nameKey]['net_per_hour'];
    $better = 0;
    foreach ($standings as $entry) {
        if ($entry['net_per_hour'] > $best) {
            $better++;
        }
    }
    respond(200, board($standings) + ['rank' => $better + 1, 'best' => $best, 'name' => $name]);
}

try {
    match ($_SERVER['REQUEST_METHOD'] ?? 'GET') {
        'GET' => handle_get(),
        'POST' => handle_post(),
        default => fail(405, 'Method not allowed'),
    };
} catch (Throwable $e) {
    error_log('leaderboard.php: ' . $e->getMessage());
    fail(500, 'Leaderboard error');
}
