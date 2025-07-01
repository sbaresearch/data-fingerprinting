# Leaderboard Phase 2

<table id="leaderboard_phase2"></table>

<script>
fetch('leaderboard_phase2.csv')
  .then(res => res.text())
  .then(text => {
    const rows = text.trim().split('\n').map(r => r.split(','));
    const table = document.getElementById('leaderboard_phase2');

    table.innerHTML = rows.map((row, i) =>
      '<tr>' + row.map(cell => `<${i === 0 ? 'th' : 'td'}>${cell}</${i === 0 ? 'th' : 'td'}>`).join('') + '</tr>'
    ).join('');
  });
</script>
