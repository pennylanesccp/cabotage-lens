[CmdletBinding()]
param(
    [string[]]$Years = @("2025", "2026"),
    [double]$MaxGapHours = 240.0,
    [string]$OutputPath = "data/processed/cabotage_data/antaq_cabotage_observed_voyages.json"
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$RawDir = Join-Path $RepoRoot "data/raw/cabotage_data"
$PortsPath = Join-Path $RepoRoot "data/processed/cabotage_data/ports_br.json"
$ResolvedOutputPath = Join-Path $RepoRoot $OutputPath

Add-Type -AssemblyName Microsoft.VisualBasic

function Convert-ToAsciiKey {
    param([string]$Value)

    $rawValue = if ($null -eq $Value) { "" } else { [string]$Value }
    $formD = $rawValue.Normalize([Text.NormalizationForm]::FormD)
    $sb = New-Object System.Text.StringBuilder
    foreach ($ch in $formD.ToCharArray()) {
        if ([Globalization.CharUnicodeInfo]::GetUnicodeCategory($ch) -ne [Globalization.UnicodeCategory]::NonSpacingMark) {
            [void]$sb.Append($ch)
        }
    }

    $ascii = $sb.ToString().Normalize([Text.NormalizationForm]::FormC).ToLowerInvariant()
    $ascii = $ascii -replace "[^a-z0-9]+", "_"
    return $ascii.Trim("_")
}

function Normalize-PortKey {
    param([string]$Value)
    $rawValue = if ($null -eq $Value) { "" } else { [string]$Value }
    return $rawValue.Trim().ToUpperInvariant()
}

function Parse-Decimal {
    param([string]$Value)

    $raw = if ($null -eq $Value) { "" } else { [string]$Value }
    $raw = $raw.Trim()
    if ([string]::IsNullOrWhiteSpace($raw)) {
        return 0.0
    }

    $normalized = $raw.Replace(" ", "")
    $normalized = $normalized -replace "[^0-9,\.\-+]", ""
    $normalized = $normalized.Replace(",", ".")
    if ([string]::IsNullOrWhiteSpace($normalized)) {
        return 0.0
    }

    $parsed = 0.0
    if ([double]::TryParse($normalized, [Globalization.NumberStyles]::Float, [Globalization.CultureInfo]::InvariantCulture, [ref]$parsed)) {
        return $parsed
    }

    return 0.0
}

function Parse-AntaqDate {
    param([string]$Value)

    $raw = if ($null -eq $Value) { "" } else { [string]$Value }
    $raw = $raw.Trim()
    if ([string]::IsNullOrWhiteSpace($raw)) {
        return $null
    }

    return [datetime]::ParseExact($raw, "dd/MM/yyyy HH:mm:ss", [Globalization.CultureInfo]::InvariantCulture)
}

function Format-DateIso {
    param($Value)

    if ($null -eq $Value) {
        return $null
    }

    return ([datetime]$Value).ToString("yyyy-MM-ddTHH:mm:ss")
}

function Round-Number {
    param([double]$Value)
    return [math]::Round($Value, 3)
}

function New-HeaderIndexMap {
    param([string[]]$Header)

    $map = @{}
    for ($i = 0; $i -lt $Header.Length; $i++) {
        $map[(Convert-ToAsciiKey $Header[$i])] = $i
    }
    return $map
}

function New-Parser {
    param([string]$Path)

    $parser = New-Object Microsoft.VisualBasic.FileIO.TextFieldParser($Path)
    $parser.TextFieldType = [Microsoft.VisualBasic.FileIO.FieldType]::Delimited
    $parser.SetDelimiters(";")
    $parser.HasFieldsEnclosedInQuotes = $true
    return $parser
}

function Get-Field {
    param(
        [string[]]$Fields,
        [hashtable]$IndexMap,
        [string]$Key
    )

    if (-not $IndexMap.ContainsKey($Key)) {
        return ""
    }

    $idx = [int]$IndexMap[$Key]
    if ($idx -ge $Fields.Length) {
        return ""
    }

    return $Fields[$idx]
}

function Build-PortAliasMap {
    param([string]$Path)

    $map = @{}
    if (-not (Test-Path $Path)) {
        return $map
    }

    $ports = Get-Content $Path -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($port in $ports) {
        $canonicalName = [string]$port.name
        $aliases = @($canonicalName, [string]$port.city)
        if ($null -ne $port.aliases) {
            $aliases += @($port.aliases)
        }

        foreach ($alias in $aliases) {
            $key = Normalize-PortKey ([string]$alias)
            if (-not [string]::IsNullOrWhiteSpace($key) -and -not $map.ContainsKey($key)) {
                $map[$key] = $canonicalName
            }
        }
    }

    return $map
}

function Read-AtracacaoMap {
    param([string[]]$YearsToRead)

    $map = @{}
    $rowCount = 0

    foreach ($year in $YearsToRead) {
        $path = Join-Path $RawDir ("{0}Atracacao.txt" -f $year)
        if (-not (Test-Path $path)) {
            throw "Missing file: $path"
        }

        $parser = New-Parser $path
        $header = $parser.ReadFields()
        $idx = New-HeaderIndexMap $header

        while (-not $parser.EndOfData) {
            $fields = $parser.ReadFields()
            $rowCount += 1

            $idAtr = Get-Field $fields $idx "idatracacao"
            if ([string]::IsNullOrWhiteSpace($idAtr)) {
                continue
            }

            $map[$idAtr] = @{
                id_atracacao = $idAtr
                year = $year
                imo = (Get-Field $fields $idx "n_do_imo").Trim()
                atracacao_at = Parse-AntaqDate (Get-Field $fields $idx "data_atracacao")
                chegada_at = Parse-AntaqDate (Get-Field $fields $idx "data_chegada")
                desatracacao_at = Parse-AntaqDate (Get-Field $fields $idx "data_desatracacao")
                porto_atracacao = (Get-Field $fields $idx "porto_atracacao").Trim()
                municipio = (Get-Field $fields $idx "municipio").Trim()
                uf = (Get-Field $fields $idx "uf").Trim()
                terminal = (Get-Field $fields $idx "terminal").Trim()
                cdtup = (Get-Field $fields $idx "cdtup").Trim()
                tipo_navegacao_atracacao = (Get-Field $fields $idx "tipo_de_navegacao_da_atracacao").Trim()
                tipo_operacao = (Get-Field $fields $idx "tipo_de_operacao").Trim()
            }
        }

        $parser.Close()
    }

    return @{
        map = $map
        row_count = $rowCount
    }
}

function New-TimeMetricsEmpty {
    return @{
        wait_for_berth_hours = 0.0
        wait_for_operation_start_hours = 0.0
        operation_hours = 0.0
        wait_for_departure_hours = 0.0
        berth_time_hours = 0.0
        port_stay_hours = 0.0
        source_row_count = 0
    }
}

function Copy-TimeMetrics {
    param([hashtable]$TimeMetrics)

    return @{
        wait_for_berth_hours = $TimeMetrics.wait_for_berth_hours
        wait_for_operation_start_hours = $TimeMetrics.wait_for_operation_start_hours
        operation_hours = $TimeMetrics.operation_hours
        wait_for_departure_hours = $TimeMetrics.wait_for_departure_hours
        berth_time_hours = $TimeMetrics.berth_time_hours
        port_stay_hours = $TimeMetrics.port_stay_hours
        source_row_count = $TimeMetrics.source_row_count
    }
}

function Merge-TimeMetrics {
    param(
        [hashtable]$Target,
        [hashtable]$Incoming
    )

    foreach ($metric in @(
        "wait_for_berth_hours",
        "wait_for_operation_start_hours",
        "operation_hours",
        "wait_for_departure_hours",
        "berth_time_hours",
        "port_stay_hours"
    )) {
        $Target[$metric] += $Incoming[$metric]
    }

    $Target.source_row_count += $Incoming.source_row_count
}

function Read-TemposAtracacaoMap {
    param([string[]]$YearsToRead)

    $map = @{}
    $rowCount = 0

    foreach ($year in $YearsToRead) {
        $path = Join-Path $RawDir ("{0}TemposAtracacao.txt" -f $year)
        if (-not (Test-Path $path)) {
            throw "Missing file: $path"
        }

        $parser = New-Parser $path
        $header = $parser.ReadFields()
        $idx = New-HeaderIndexMap $header

        while (-not $parser.EndOfData) {
            $fields = $parser.ReadFields()
            $rowCount += 1

            $idAtr = Get-Field $fields $idx "idatracacao"
            if ([string]::IsNullOrWhiteSpace($idAtr)) {
                continue
            }

            $map[$idAtr] = @{
                id_atracacao = $idAtr
                wait_for_berth_hours = Parse-Decimal (Get-Field $fields $idx "tesperaatracacao")
                wait_for_operation_start_hours = Parse-Decimal (Get-Field $fields $idx "tesperainicioop")
                operation_hours = Parse-Decimal (Get-Field $fields $idx "toperacao")
                wait_for_departure_hours = Parse-Decimal (Get-Field $fields $idx "tesperadesatracacao")
                berth_time_hours = Parse-Decimal (Get-Field $fields $idx "tatracado")
                port_stay_hours = Parse-Decimal (Get-Field $fields $idx "testadia")
            }
        }

        $parser.Close()
    }

    return @{
        map = $map
        row_count = $rowCount
    }
}

function New-CallStats {
    param([string]$IdAtracacao)

    return @{
        id_atracacao = $IdAtracacao
        rows = 0
        moved_teu = 0.0
        moved_weight_t = 0.0
        loaded_teu = 0.0
        loaded_weight_t = 0.0
        unloaded_teu = 0.0
        unloaded_weight_t = 0.0
        local_codes = @{}
    }
}

function Add-LocalCodeSample {
    param(
        [hashtable]$CallStats,
        [string]$Code,
        [double]$Teu,
        [double]$WeightT
    )

    $key = Normalize-PortKey $Code
    if ([string]::IsNullOrWhiteSpace($key)) {
        return
    }

    if (-not $CallStats.local_codes.ContainsKey($key)) {
        $CallStats.local_codes[$key] = @{
            rows = 0
            teu = 0.0
            weight_t = 0.0
        }
    }

    $bucket = $CallStats.local_codes[$key]
    $bucket.rows += 1
    $bucket.teu += $Teu
    $bucket.weight_t += $WeightT
}

function Is-ContainerizedCabotage {
    param(
        [string]$TipoNavegacao,
        [double]$Teu,
        [string]$Natureza,
        [string]$Acondicionamento
    )

    $tipo = if ($null -eq $TipoNavegacao) { "" } else { [string]$TipoNavegacao }
    if ($tipo.Trim().ToLowerInvariant() -ne "cabotagem") {
        return $false
    }

    if ($Teu -gt 0) {
        return $true
    }

    $naturezaText = if ($null -eq $Natureza) { "" } else { [string]$Natureza }
    $acondText = if ($null -eq $Acondicionamento) { "" } else { [string]$Acondicionamento }
    $naturezaText = $naturezaText.ToLowerInvariant()
    $acondText = $acondText.ToLowerInvariant()
    return $naturezaText.Contains("conteiner") -or $acondText.Contains("conteiner")
}

function Read-CargaCallStats {
    param([string[]]$YearsToRead)

    $callStatsMap = @{}
    $processedRows = 0
    $keptRows = 0

    foreach ($year in $YearsToRead) {
        $path = Join-Path $RawDir ("{0}Carga.txt" -f $year)
        if (-not (Test-Path $path)) {
            throw "Missing file: $path"
        }

        $parser = New-Parser $path
        $header = $parser.ReadFields()
        $idx = New-HeaderIndexMap $header

        while (-not $parser.EndOfData) {
            $fields = $parser.ReadFields()
            $processedRows += 1

            $teu = Parse-Decimal (Get-Field $fields $idx "teu")
            $tipoNavegacao = Get-Field $fields $idx "tipo_navegacao"
            $natureza = Get-Field $fields $idx "natureza_da_carga"
            $acondicionamento = Get-Field $fields $idx "carga_geral_acondicionamento"

            if (-not (Is-ContainerizedCabotage $tipoNavegacao $teu $natureza $acondicionamento)) {
                continue
            }

            $idAtr = Get-Field $fields $idx "idatracacao"
            if ([string]::IsNullOrWhiteSpace($idAtr)) {
                continue
            }

            if (-not $callStatsMap.ContainsKey($idAtr)) {
                $callStatsMap[$idAtr] = New-CallStats $idAtr
            }

            $stats = $callStatsMap[$idAtr]
            $weightT = Parse-Decimal (Get-Field $fields $idx "vlpesocargabruta")
            $sentido = (Get-Field $fields $idx "sentido").Trim().ToLowerInvariant()
            $origem = Get-Field $fields $idx "origem"
            $destino = Get-Field $fields $idx "destino"

            $stats.rows += 1
            $stats.moved_teu += $teu
            $stats.moved_weight_t += $weightT
            $keptRows += 1

            if ($sentido.StartsWith("embarc")) {
                $stats.loaded_teu += $teu
                $stats.loaded_weight_t += $weightT
                Add-LocalCodeSample $stats $origem $teu $weightT
            }
            elseif ($sentido.StartsWith("desembarc")) {
                $stats.unloaded_teu += $teu
                $stats.unloaded_weight_t += $weightT
                Add-LocalCodeSample $stats $destino $teu $weightT
            }
            else {
                Add-LocalCodeSample $stats $origem $teu $weightT
                Add-LocalCodeSample $stats $destino $teu $weightT
            }
        }

        $parser.Close()
    }

    return @{
        map = $callStatsMap
        processed_rows = $processedRows
        kept_rows = $keptRows
    }
}

function Resolve-DominantPortCode {
    param([hashtable]$CallStats)

    $bestCode = ""
    $bestWeight = -1.0
    $bestTeu = -1.0
    $bestRows = -1

    foreach ($entry in $CallStats.local_codes.GetEnumerator()) {
        $code = [string]$entry.Key
        $stats = $entry.Value
        if (
            ($stats.weight_t -gt $bestWeight) -or
            (($stats.weight_t -eq $bestWeight) -and ($stats.teu -gt $bestTeu)) -or
            (($stats.weight_t -eq $bestWeight) -and ($stats.teu -eq $bestTeu) -and ($stats.rows -gt $bestRows)) -or
            (($stats.weight_t -eq $bestWeight) -and ($stats.teu -eq $bestTeu) -and ($stats.rows -eq $bestRows) -and ($code -lt $bestCode))
        ) {
            $bestCode = $code
            $bestWeight = $stats.weight_t
            $bestTeu = $stats.teu
            $bestRows = $stats.rows
        }
    }

    return $bestCode
}

function Resolve-PortName {
    param(
        [string]$PortCode,
        [string]$FallbackName,
        [hashtable]$AliasMap
    )

    $code = Normalize-PortKey $PortCode
    if (-not [string]::IsNullOrWhiteSpace($code) -and $AliasMap.ContainsKey($code)) {
        return $AliasMap[$code]
    }

    $fallback = if ($null -eq $FallbackName) { "" } else { [string]$FallbackName }
    $fallback = $fallback.Trim()
    if (-not [string]::IsNullOrWhiteSpace($fallback)) {
        $fallbackKey = Normalize-PortKey $fallback
        if ($AliasMap.ContainsKey($fallbackKey)) {
            return $AliasMap[$fallbackKey]
        }
        return $fallback
    }

    return $code
}

function New-StopInternal {
    param(
        [hashtable]$Meta,
        [hashtable]$CallStats,
        [hashtable]$AliasMap,
        [hashtable]$TimeRow
    )

    $portCode = Resolve-DominantPortCode $CallStats
    $portName = Resolve-PortName $portCode $Meta.porto_atracacao $AliasMap
    $portKey = if (-not [string]::IsNullOrWhiteSpace($portCode)) {
        $portCode
    }
    else {
        Normalize-PortKey $Meta.porto_atracacao
    }
    $timeMetrics = if ($null -ne $TimeRow) {
        @{
            wait_for_berth_hours = $TimeRow.wait_for_berth_hours
            wait_for_operation_start_hours = $TimeRow.wait_for_operation_start_hours
            operation_hours = $TimeRow.operation_hours
            wait_for_departure_hours = $TimeRow.wait_for_departure_hours
            berth_time_hours = $TimeRow.berth_time_hours
            port_stay_hours = $TimeRow.port_stay_hours
            source_row_count = 1
        }
    }
    else {
        New-TimeMetricsEmpty
    }

    return @{
        port_key = $portKey
        port_code = $portCode
        port_name = $portName
        atracacao_port_name = $Meta.porto_atracacao
        municipio = $Meta.municipio
        uf = $Meta.uf
        first_at = $Meta.atracacao_at
        last_at = if ($null -ne $Meta.desatracacao_at) { $Meta.desatracacao_at } else { $Meta.atracacao_at }
        call_ids = New-Object System.Collections.ArrayList
        call_count = 1
        time = $timeMetrics
        cargo = @{
            loaded_teu = $CallStats.loaded_teu
            loaded_weight_t = $CallStats.loaded_weight_t
            unloaded_teu = $CallStats.unloaded_teu
            unloaded_weight_t = $CallStats.unloaded_weight_t
            moved_teu = $CallStats.moved_teu
            moved_weight_t = $CallStats.moved_weight_t
            net_teu = ($CallStats.loaded_teu - $CallStats.unloaded_teu)
            net_weight_t = ($CallStats.loaded_weight_t - $CallStats.unloaded_weight_t)
        }
    }
}

function Copy-StopInternal {
    param([hashtable]$Stop)

    $copy = @{
        port_key = $Stop.port_key
        port_code = $Stop.port_code
        port_name = $Stop.port_name
        atracacao_port_name = $Stop.atracacao_port_name
        municipio = $Stop.municipio
        uf = $Stop.uf
        first_at = $Stop.first_at
        last_at = $Stop.last_at
        call_ids = New-Object System.Collections.ArrayList
        call_count = $Stop.call_count
        time = (Copy-TimeMetrics $Stop.time)
        cargo = @{
            loaded_teu = $Stop.cargo.loaded_teu
            loaded_weight_t = $Stop.cargo.loaded_weight_t
            unloaded_teu = $Stop.cargo.unloaded_teu
            unloaded_weight_t = $Stop.cargo.unloaded_weight_t
            moved_teu = $Stop.cargo.moved_teu
            moved_weight_t = $Stop.cargo.moved_weight_t
            net_teu = $Stop.cargo.net_teu
            net_weight_t = $Stop.cargo.net_weight_t
        }
    }

    foreach ($callId in $Stop.call_ids) {
        [void]$copy.call_ids.Add($callId)
    }

    return $copy
}

function Merge-StopsInternal {
    param(
        [hashtable]$Target,
        [hashtable]$Incoming
    )

    if ($Incoming.first_at -lt $Target.first_at) {
        $Target.first_at = $Incoming.first_at
    }
    if ($Incoming.last_at -gt $Target.last_at) {
        $Target.last_at = $Incoming.last_at
    }

    $Target.call_count += $Incoming.call_count
    Merge-TimeMetrics $Target.time $Incoming.time
    foreach ($callId in $Incoming.call_ids) {
        [void]$Target.call_ids.Add($callId)
    }

    foreach ($metric in @("loaded_teu", "loaded_weight_t", "unloaded_teu", "unloaded_weight_t", "moved_teu", "moved_weight_t", "net_teu", "net_weight_t")) {
        $Target.cargo[$metric] += $Incoming.cargo[$metric]
    }
}

function Convert-StopToOutput {
    param(
        [hashtable]$Stop,
        [int]$Sequence
    )

    $observedSpanHours = if (($null -ne $Stop.first_at) -and ($null -ne $Stop.last_at)) {
        Round-Number ((($Stop.last_at) - ($Stop.first_at)).TotalHours)
    }
    else {
        $null
    }

    return [ordered]@{
        sequence = $Sequence
        port_key = $Stop.port_key
        port_code = $Stop.port_code
        port_name = $Stop.port_name
        atracacao_port_name = $Stop.atracacao_port_name
        municipality = $Stop.municipio
        state = $Stop.uf
        first_atracacao_at = Format-DateIso $Stop.first_at
        last_atracacao_at = Format-DateIso $Stop.last_at
        call_count = $Stop.call_count
        call_ids = @($Stop.call_ids)
        time = [ordered]@{
            observed_span_hours = $observedSpanHours
            wait_for_berth_hours = Round-Number $Stop.time.wait_for_berth_hours
            wait_for_operation_start_hours = Round-Number $Stop.time.wait_for_operation_start_hours
            operation_hours = Round-Number $Stop.time.operation_hours
            wait_for_departure_hours = Round-Number $Stop.time.wait_for_departure_hours
            berth_time_hours = Round-Number $Stop.time.berth_time_hours
            port_stay_hours = Round-Number $Stop.time.port_stay_hours
            source_row_count = $Stop.time.source_row_count
        }
        cargo = [ordered]@{
            loaded_teu = Round-Number $Stop.cargo.loaded_teu
            loaded_weight_t = Round-Number $Stop.cargo.loaded_weight_t
            unloaded_teu = Round-Number $Stop.cargo.unloaded_teu
            unloaded_weight_t = Round-Number $Stop.cargo.unloaded_weight_t
            moved_teu = Round-Number $Stop.cargo.moved_teu
            moved_weight_t = Round-Number $Stop.cargo.moved_weight_t
            net_teu = Round-Number $Stop.cargo.net_teu
            net_weight_t = Round-Number $Stop.cargo.net_weight_t
        }
    }
}

function Finalize-Voyage {
    param(
        [string]$Imo,
        [int]$VoyageIndex,
        [System.Collections.ArrayList]$Stops,
        [bool]$ClosedLoop,
        [string]$ClosedBy
    )

    if ($Stops.Count -lt 2) {
        return $null
    }

    $outputStops = New-Object System.Collections.ArrayList
    for ($i = 0; $i -lt $Stops.Count; $i++) {
        [void]$outputStops.Add((Convert-StopToOutput $Stops[$i] $i))
    }

    $origin = $outputStops[0]
    $destination = $outputStops[$outputStops.Count - 1]
    $intermediateStops = if ($outputStops.Count -gt 2) {
        @($outputStops | Select-Object -Skip 1 -First ($outputStops.Count - 2))
    }
    else {
        @()
    }

    return [ordered]@{
        voyage_id = ("voyage_{0}_{1:D5}" -f $Imo, $VoyageIndex)
        imo = $Imo
        closed_loop = $ClosedLoop
        closed_by = $ClosedBy
        stop_count = $outputStops.Count
        started_at = $origin.first_atracacao_at
        ended_at = $destination.last_atracacao_at
        origin_port_code = $origin.port_code
        origin_port_name = $origin.port_name
        destination_port_code = $destination.port_code
        destination_port_name = $destination.port_name
        origin_time = $origin.time
        destination_time = $destination.time
        origin_cargo = $origin.cargo
        destination_cargo = $destination.cargo
        intermediate_stop_count = $intermediateStops.Count
        intermediate_stops = [object[]]$intermediateStops
        stops = [object[]]@($outputStops)
    }
}

function Build-ObservedVoyages {
    param(
        [hashtable]$AtracacaoMap,
        [hashtable]$CallStatsMap,
        [hashtable]$TemposAtracacaoMap,
        [hashtable]$AliasMap,
        [double]$GapHours
    )

    $callsByImo = @{}
    $joinedCalls = 0
    $droppedWithoutAtracacao = 0
    $droppedWithoutImo = 0
    $callsWithTimeMetrics = 0
    $callsWithoutTimeMetrics = 0

    foreach ($entry in $CallStatsMap.GetEnumerator()) {
        $idAtr = [string]$entry.Key
        $callStats = $entry.Value

        if (-not $AtracacaoMap.ContainsKey($idAtr)) {
            $droppedWithoutAtracacao += 1
            continue
        }

        $meta = $AtracacaoMap[$idAtr]
        $imo = if ($null -eq $meta.imo) { "" } else { [string]$meta.imo }
        $imo = $imo.Trim()
        if ([string]::IsNullOrWhiteSpace($imo)) {
            $droppedWithoutImo += 1
            continue
        }

        $timeRow = $null
        if ($TemposAtracacaoMap.ContainsKey($idAtr)) {
            $timeRow = $TemposAtracacaoMap[$idAtr]
            $callsWithTimeMetrics += 1
        }
        else {
            $callsWithoutTimeMetrics += 1
        }

        $stop = New-StopInternal $meta $callStats $AliasMap $timeRow
        [void]$stop.call_ids.Add($idAtr)

        if (-not $callsByImo.ContainsKey($imo)) {
            $callsByImo[$imo] = New-Object System.Collections.ArrayList
        }

        [void]$callsByImo[$imo].Add($stop)
        $joinedCalls += 1
    }

    $voyages = New-Object System.Collections.ArrayList
    $collapsedStopsCount = 0

    foreach ($imo in ($callsByImo.Keys | Sort-Object)) {
        $orderedCalls = @(
            $callsByImo[$imo] | Sort-Object `
                @{ Expression = { $_.first_at } }, `
                @{ Expression = { $_.last_at } }, `
                @{ Expression = { $_.port_key } }
        )
        if ($orderedCalls.Count -eq 0) {
            continue
        }

        $collapsedStops = New-Object System.Collections.ArrayList
        $currentStop = Copy-StopInternal $orderedCalls[0]

        for ($i = 1; $i -lt $orderedCalls.Count; $i++) {
            $nextStop = $orderedCalls[$i]
            if (
                ($currentStop.port_key -eq $nextStop.port_key) -and
                (-not [string]::IsNullOrWhiteSpace($currentStop.port_key))
            ) {
                Merge-StopsInternal $currentStop $nextStop
                continue
            }

            [void]$collapsedStops.Add($currentStop)
            $currentStop = Copy-StopInternal $nextStop
        }

        [void]$collapsedStops.Add($currentStop)
        $collapsedStopsCount += $collapsedStops.Count

        if ($collapsedStops.Count -lt 2) {
            continue
        }

        $voyageIndex = 1
        $workingStops = New-Object System.Collections.ArrayList
        [void]$workingStops.Add((Copy-StopInternal $collapsedStops[0]))

        for ($i = 1; $i -lt $collapsedStops.Count; $i++) {
            $nextStop = $collapsedStops[$i]
            $prevStop = $workingStops[$workingStops.Count - 1]
            $gap = (($nextStop.first_at) - ($prevStop.last_at)).TotalHours

            if ($gap -gt $GapHours) {
                $voyage = Finalize-Voyage $imo $voyageIndex $workingStops $false "gap"
                if ($null -ne $voyage) {
                    [void]$voyages.Add($voyage)
                    $voyageIndex += 1
                }

                $workingStops = New-Object System.Collections.ArrayList
                [void]$workingStops.Add((Copy-StopInternal $nextStop))
                continue
            }

            [void]$workingStops.Add((Copy-StopInternal $nextStop))

            if (($workingStops.Count -ge 3) -and ($workingStops[$workingStops.Count - 1].port_key -eq $workingStops[0].port_key)) {
                $voyage = Finalize-Voyage $imo $voyageIndex $workingStops $true "return_to_origin"
                if ($null -ne $voyage) {
                    [void]$voyages.Add($voyage)
                    $voyageIndex += 1
                }

                $workingStops = New-Object System.Collections.ArrayList
                [void]$workingStops.Add((Copy-StopInternal $nextStop))
            }
        }

        $tailVoyage = Finalize-Voyage $imo $voyageIndex $workingStops $false "open_tail"
        if ($null -ne $tailVoyage) {
            [void]$voyages.Add($tailVoyage)
        }
    }

    return @{
        voyages = $voyages
        joined_calls = $joinedCalls
        dropped_without_atracacao = $droppedWithoutAtracacao
        dropped_without_imo = $droppedWithoutImo
        calls_with_time_metrics = $callsWithTimeMetrics
        calls_without_time_metrics = $callsWithoutTimeMetrics
        unique_imos = $callsByImo.Keys.Count
        collapsed_stops = $collapsedStopsCount
    }
}

$aliasMap = Build-PortAliasMap $PortsPath
$atracacaoResult = Read-AtracacaoMap $Years
$temposAtracacaoResult = Read-TemposAtracacaoMap $Years
$cargaResult = Read-CargaCallStats $Years
$voyageResult = Build-ObservedVoyages $atracacaoResult.map $cargaResult.map $temposAtracacaoResult.map $aliasMap $MaxGapHours

$payload = [ordered]@{
    generated_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ss")
    years = $Years
    source_files = [ordered]@{
        atracacao = @($Years | ForEach-Object { "data/raw/cabotage_data/{0}Atracacao.txt" -f $_ })
        carga = @($Years | ForEach-Object { "data/raw/cabotage_data/{0}Carga.txt" -f $_ })
        tempos_atracacao = @($Years | ForEach-Object { "data/raw/cabotage_data/{0}TemposAtracacao.txt" -f $_ })
    }
    filters = [ordered]@{
        tipo_navegacao_carga = "Cabotagem"
        containerized_rule = "TEU > 0 or cargo labels contain 'conteiner'"
        imo_required = $true
    }
    segmentation = [ordered]@{
        consecutive_same_port_calls_collapsed = $true
        voyage_closed_when_returning_to_origin_port = $true
        max_gap_hours_between_stops = $MaxGapHours
        note = "First and last voyages for an IMO can be partial because the observation window is limited."
    }
    stats = [ordered]@{
        atracacao_rows = $atracacaoResult.row_count
        tempos_atracacao_rows = $temposAtracacaoResult.row_count
        carga_rows_processed = $cargaResult.processed_rows
        carga_rows_kept = $cargaResult.kept_rows
        joined_calls = $voyageResult.joined_calls
        dropped_calls_without_atracacao = $voyageResult.dropped_without_atracacao
        dropped_calls_without_imo = $voyageResult.dropped_without_imo
        joined_calls_with_time_metrics = $voyageResult.calls_with_time_metrics
        joined_calls_without_time_metrics = $voyageResult.calls_without_time_metrics
        unique_imos = $voyageResult.unique_imos
        collapsed_stops = $voyageResult.collapsed_stops
        voyages = $voyageResult.voyages.Count
    }
    voyages = @($voyageResult.voyages)
}

$outputDir = Split-Path -Parent $ResolvedOutputPath
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
$payload | ConvertTo-Json -Depth 8 | Set-Content -Path $ResolvedOutputPath -Encoding UTF8

Write-Output ("Wrote JSON: {0}" -f $ResolvedOutputPath)
Write-Output ("Voyages: {0}" -f $payload.stats.voyages)
Write-Output ("Unique IMOs: {0}" -f $payload.stats.unique_imos)
